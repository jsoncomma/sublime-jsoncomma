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

LAST_RELEASE_STORE = "jsoncomma_binary_last_release"


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
        running, msg = cls.is_ready()
        assert running is False, "msg: {}, process: {}, infos: {}".format(
            msg, cls.process, cls.infos
        )

        settings = sublime.load_settings(SETTINGS)
        executable_path = settings.get(SETTINGS_EXECUTABLE)
        executable_path = os.path.expandvars(os.path.expanduser(executable_path))

        if not os.path.exists(executable_path):
            if confirm_automatic_download(executable_path):
                try:
                    executable_path = cls.update_binary()
                except Exception as e:
                    notify("failed to download binary: {}", e)
                    raise e
                else:
                    notify("done downloading jsoncomma to {}".format(executable_path))
            else:
                notify(
                    "executable_path {} doesn't exist, server can't be started.",
                    executable_path,
                )
                # no executable to be found, and the user doesn't want auto installs
                return

        elif settings.get(SETTINGS_AUTO_UPDATE):
            # check for update
            # FIXME: this shouldn't be done at *every* startup.
            new_path = cls.update_binary()
            # new path is none if no update was required
            if new_path is not None:
                executable_path = new_path

        cls._start(executable_path)

    @classmethod
    def _start(cls, executable_path: str):
        """ Just starts the actual process
        """

        # hide the terminal window on Windows
        startupinfo = None
        if os.name == "nt":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        cls.process = subprocess.Popen(
            [executable_path, "server", "-host", "localhost", "-port", "0"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            startupinfo=startupinfo,
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
            print("output from the server: {!r}".format(line))
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

        notify("server started on {}", cls.infos["addr"])

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

        cls.process.terminate()
        try:
            cls.process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            notify("had to kill (SIGKILL) process after 1 second timeout")
            cls.process.kill()

        cls.process = None
        cls.infos = None
        sublime.status_message("JSONComma: server stopped")

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

    # downloading/updating the binary

    @classmethod
    def get_last_release(cls) -> str:
        """ Gets the latest tag name.
        """
        notify("checking last release...")
        try:
            resp = requests.get(
                "https://api.github.com/repos/jsoncomma/jsoncomma/releases"
            )
        except requests.ConnectionError as e:
            notify("couldn't check last version: {}", e)
            raise e

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
            return release["tag_name"]

        assert False, "no non-draft or non-prerelease release found"

    @classmethod
    def update_binary(cls):
        """ install the binary in the right location, and store the path in settings.
        It returns the location of the binary. This function blocks. """

        latest_tag_name = cls.get_last_release()
        try:
            with open(
                os.path.join(sublime.packages_path(), "User", LAST_RELEASE_STORE)
            ) as fp:
                installed_tag_name = fp.read()
        except FileNotFoundError:
            # do download the server, because there is currently nothing installed
            pass
        else:
            # compare the tag name, and if it's different (assume it's older), download the update
            if installed_tag_name == latest_tag_name:
                notify("latest release installed already")
                return
        notify("downloading latest version of jsoncomma {}", latest_tag_name)

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

        paths = {
            # sublime.platform() -> path for executable
            "windows": "%APPDATA%\\jsoncomma\\jsoncomma.exe",
            "linux": "~/.config/jsoncomma/jsoncomma",
            "osx": "~/Library/Application Support/jsoncomma/jsoncomma",
        }

        download_url = (
            "https://github.com/jsoncomma/jsoncomma/releases/download/"
            "{tag_name}/jsoncomma_{tag_name}_{platform}_{arch}.tar.gz".format(
                tag_name=latest_tag_name,
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

        executable_path = os.path.expanduser(
            os.path.expandvars(paths[sublime.platform()])
        )

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

        settings = sublime.load_settings(SETTINGS)
        # don't save executable_path because the variables in there
        # are expanded (eg. there is no ~, but C:\Users\<username>). It's bad
        # because it breaks portability (if the user shared his config between
        # two machines, having the variables still in the paths is much better
        # because the config might still work even if the values of the variables
        # are different)
        settings.set(SETTINGS_EXECUTABLE, paths[sublime.platform()])
        sublime.save_settings(SETTINGS)

        with open(
            os.path.join(sublime.packages_path(), "User", LAST_RELEASE_STORE), "w"
        ) as fp:
            fp.write(latest_tag_name)

        notify("done, jsoncomma binary at {!r}", executable_path)

        # FIXME: maybe we should have a platform dependent settings file...
        return executable_path


def confirm_automatic_download(current_path):
    # I'm not sure how I can make it clear that this is a one time thing.
    # if the user wants to update the server, he will have to do so manually
    return sublime.ok_cancel_dialog(
        "The jsoncomma server was not found at '{}'. "
        "However, it needs to be installed for JSONComma to work. "
        "More details can be found at https://jsoncomma.github.io"
        "\n\n"
        "Do you want JSONComma to install it for you?".format(current_path),
        "Download jsoncomma for me",
    )


def notify(format, *args, **kwargs):
    message = "JSONComma: " + format.format(*args, **kwargs)
    print(message)
    sublime.status_message(message)
