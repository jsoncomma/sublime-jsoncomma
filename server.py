import sublime
import os
import stat
import requests
import subprocess
import json
import tarfile
import shutil
import io


SETTINGS = "JSONComma.sublime-settings"
SETTINGS_EXECUTABLE = "executable_path"
SETTINGS_AUTO_UPDATE = "automatically_update_executable"


class server:
    process = None
    infos = None
    downloading = False

    @classmethod
    def is_ready(cls):
        if cls.downloading is True:
            return False, "downloading the server (json executable)"
        if cls.process is None:
            return False, "the server process isn't running"
        if cls.infos is None:
            return False, "still gatherring information about hte server's address"
        return True, ""

    @classmethod
    def start(cls):
        """ Starts the server, downloading updates if needed
        """

        running, msg = cls.is_ready()
        assert running is False, "msg: {}, process: {}, infos: {}".format(
            msg, cls.process, cls.infos
        )

        # this is some shit logic, but it needs to cover all those paths
        # auto updates on, executable doesn't exists (require update)
        # auto updates on, executable exists (try to update)
        # auto updates off, exectuable doesn't exists (ask to enable auto updates)
        # auto updates off, exectuable exists (start process)
        # TODO: add in yes/no from user

        settings = sublime.load_settings(SETTINGS)

        if settings.get(SETTINGS_AUTO_UPDATE):
            executable_path = cls.get_default_executable_path(expand_vars=True)
        else:
            executable_path = settings.get(SETTINGS_EXECUTABLE)
            executable_path = os.path.expanduser(os.path.expandvars(executable_path))

        if not os.path.exists(executable_path):
            if not confirm_automatic_download(executable_path):
                notify(
                    "no binary found, and automatic updates disabled. JSONComma will not work"
                )
                settings.set(SETTINGS_AUTO_UPDATE, False)
                sublime.save_settings(SETTINGS)
                return

            settings.set(SETTINGS_AUTO_UPDATE, True)
            sublime.save_settings(SETTINGS)
            executable_path = cls.get_default_executable_path(expand_vars=True)

        if settings.get(SETTINGS_AUTO_UPDATE):
            try:
                cls.auto_update_executable()
            except requests.ConnectionError as e:
                print("JSONComma:", e)
                if not os.path.exists(executable_path):
                    notify(
                        "failed to download server due to network error, JSONComma won't work"
                    )
                    return
                else:
                    notify(
                        "failed to automatically download server due to network error, running current version"
                    )

        cls.process = start_process(
            [executable_path, "server", "-host", "localhost", "-port", "0"],
        )

        line = cls.process.stdout.readline().decode("utf-8")
        try:
            cls.infos = json.loads(line)
        except ValueError as e:
            sublime.error_message(
                "Failed to start jsoncomma server.\n\n{}\n\nMore details in the console".format(
                    e
                )
            )
            print("JSONComma: output from the server: {!r}".format(line))
            raise e

        assert "addr" in cls.infos, "server infos should include 'addr' ({})".format(
            cls.infos
        )
        assert "port" in cls.infos, "server infos should include 'port' ({})".format(
            cls.infos
        )
        assert "host" in cls.infos, "server infos should include 'host' ({})".format(
            cls.infos
        )

        notify("server {} started on {}", executable_path, cls.infos["addr"])

    @classmethod
    def stop(cls):
        """ stops the server

        First, try to terminate the server (SIGTERM), waiting (block) for 1
        second at most. If it doesn't shutdown in that time, then SIGKILL is
        sent.

        On windows, process.terminate() is equivalent to process.kill()
        """

        if cls.process is None:
            # we can get here if the user closes sublime whilst the server is downloading/not ready
            cls.infos = None
            return

        kill_nicely(cls.process)

        cls.process = None
        cls.infos = None
        notify("JSONComma: server stopped")

    @classmethod
    def fix(cls, json_to_fix):
        running, msg = cls.is_ready()
        if running is False:
            notify("{} (process: {}, infos: {})".format(msg, cls.process, cls.infos))
            return

        try:
            resp = requests.post("http://" + cls.infos["addr"], data=json_to_fix)
        except requests.exceptions.ConnectionError as e:
            notify("connection error with server ({})", e)
            return

        if resp.status_code != 200:
            print("response from JSONComma server:")
            print(resp)
            notify(
                "invalid response code from server (got {}, expected 200)",
                resp.status_code,
            )
            return

        if resp.headers["Content-Type"] != "text/plain; charset=utf-8":
            print("response from JSONComma server:")
            print(resp)
            notify(
                "invalid header 'Content-Type' (got {!r}, expected 'text/plain; charset=utf-8')",
                resp.headers["Content-Type"],
            )
            return

        return resp.text

    #
    # downloading/updating the binary
    #

    @classmethod
    def auto_update_executable(cls):
        """ install the binary in the right location, and store the path in settings.
        It returns the location of the binary. This function blocks. """

        assert (
            cls.downloading is False
        ), "auto_update_executable called already (cls.downloading: {})".format(
            cls.downloading
        )

        executable_path = cls.get_default_executable_path(expand_vars=True)

        latest_version = cls.get_latest_version()

        try:
            current_version = cls.get_current_executable_version(executable_path)
        except FileNotFoundError as e:
            # we are going to download it
            notify("current version: non existent, latest version: {}", latest_version)
        else:
            if current_version == latest_version:
                # don't need to update
                return executable_path

            notify(
                "current version: {}, latest version: {}".format(
                    current_version, latest_version
                )
            )

        cls.downloading = True

        platforms = {
            # sublime.plaform() -> goreleaser's platform names
            "windows": "Windows",
            "osx": "Darwin",
            "linux": "Linux",
        }

        archs = {
            # sublime.arch() -> goreleaser's arch names
            "x32": "i386",
            "x64": "x86_64",
        }

        download_url = (
            "https://github.com/jsoncomma/jsoncomma/releases/download/"
            "v{version}/jsoncomma_v{version}_{platform}_{arch}.tar.gz".format(
                version=latest_version,
                platform=platforms[sublime.platform()],
                arch=archs[sublime.arch()],
            )
        )

        notify("downloading binary from {}", download_url)

        # We don't stream the download because tarfile can't extract file if you
        # don't have a seek method (and setting stream=True gives you a file object
        # without seek)
        resp = requests.get(download_url)
        assert (
            resp.status_code == 200
        ), "[downloading] expected 200 status code, got {}".format(resp.status_code)

        os.makedirs(os.path.dirname(executable_path), exist_ok=True)

        # make sure the server is stopped before we update the binary
        cls.stop()

        notify("extracting tar...")
        with open(executable_path, "wb") as target, tarfile.open(
            mode="r:gz", fileobj=io.BytesIO(resp.content)
        ) as tar:

            for tarinfo in tar.getmembers():
                if tarinfo.name.startswith("jsoncomma"):
                    break

            notify("extracting file {!r}...", tarinfo.name)

            fileobj = tar.extractfile(tarinfo.name)
            assert fileobj is not None, "extracted {}, but got None".format(
                tarinfo.name
            )
            shutil.copyfileobj(fileobj, target)

        os.chmod(executable_path, os.stat(executable_path).st_mode | stat.S_IEXEC)

        cls.downloading = False

        # FIXME: maybe we should have a platform dependent settings file...

    @classmethod
    def get_latest_version(cls) -> str:
        """ Gets the latest version from GitHub
        """
        notify("checking last release...")
        resp = requests.get("https://api.github.com/repos/jsoncomma/jsoncomma/releases")

        assert (
            resp.status_code == 200
        ), "[getting last release] expected 200 status code, got {}".format(
            resp.status_code
        )

        releases = resp.json()
        for release in releases:
            # ignore prereleases and drafts
            if release["draft"] or release["prerelease"]:
                continue

            assert release["tag_name"].startswith(
                "v"
            ), "expected tag name to start with 'v' in {!r}".format(release["tag_name"])

            return release["tag_name"][1:]

        assert False, "no non-draft or non-prerelease release found"

    @classmethod
    def get_current_executable_version(cls, executable_path):
        process = start_process([executable_path, "-version"])
        try:
            exit_code = process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            kill_nicely(process)
            return

        if exit_code != 0:
            notify("{} -version exited with code {}", executable_path, exit_code)
            return None

        return process.stdout.readline().decode("utf-8").split(" ")[0]

    @classmethod
    def get_default_executable_path(cls, *, expand_vars):
        assert isinstance(
            expand_vars, bool
        ), "expand_vars should be a boolean, got {}".format(type(expand_vars))

        path = {
            # sublime.platform() -> path for executable
            "windows": "%APPDATA%\\jsoncomma\\jsoncomma.exe",
            "linux": "~/.config/jsoncomma/jsoncomma",
            "osx": "~/Library/Application Support/jsoncomma/jsoncomma",
        }[sublime.platform()]

        if expand_vars:
            return os.path.expandvars(os.path.expanduser(path))
        return path


def confirm_automatic_download(current_path):
    # I'm not sure how I can make it clear that this is a one time thing.
    # if the user wants to update the server, he will have to do so manually
    return sublime.ok_cancel_dialog(
        "The jsoncomma server was not found at '{}' "
        "but, it needs to be installed for JSONComma to work. "
        "More details can be found at https://jsoncomma.github.io. "
        "If you decline, automatic updates will be disabled (you can change "
        "that in JSONComma's settings)."
        "\n\n"
        "Automatic download is recommended for all users who are not "
        "currently contributing to the development to jsoncomma."
        "\n\n"
        "Do you want JSONComma to install it for you?".format(current_path),
        "Download jsoncomma for me",
    )


def notify(format, *args, **kwargs):
    message = "JSONComma: " + format.format(*args, **kwargs)
    print(message)
    sublime.status_message(message)


def start_process(cmd, *args, **kwargs):
    # hide the terminal window on Windows
    startupinfo = None
    if os.name == "nt":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    # catch stdout and stderr by default
    if "stdout" not in kwargs:
        kwargs["stdout"] = subprocess.PIPE

    if "stderr" not in kwargs:
        kwargs["stderr"] = subprocess.STDOUT

    return subprocess.Popen(cmd, startupinfo=startupinfo, *args, **kwargs)


def kill_nicely(process, *, timeout=1):
    """ tries to terminate, and then kills after timeout seconds
    returns the exit code
    """

    process.terminate()
    try:
        return process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill()
    return process.poll()
