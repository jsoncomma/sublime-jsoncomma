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


class server:
    process = None
    infos = None
    downloading = False

    @classmethod
    def assert_ready(cls):
        assert (
            cls.downloading is False
        ), "downloading the server (jsoncomma exectutable)"
        assert cls.process is not None, "the server process isn't running"
        assert (
            cls.infos is not None
        ), "still gathering information about the server's address"

    @classmethod
    def start(cls):
        try:
            cls.assert_ready()
        except AssertionError:
            pass
        else:
            raise AssertionError(
                "server already running. process: {} infos: {}".format(
                    cls.process, cls.infos
                )
            )

        executable_path = sublime.load_settings(SETTINGS).get(SETTINGS_EXECUTABLE)
        executable_path = os.path.expandvars(os.path.expanduser(executable_path))

        if not os.path.exists(executable_path):
            if confirm_automatic_download(executable_path):
                try:
                    executable_path = cls.download()
                except AssertionError as e:
                    notify("failed to download: {}", e.args[0])
                    return
                notify("done downloading jsoncomma to {}".format(executable_path))
            else:
                notify(
                    "executable_path {} doesn't exist, server can't be started.",
                    executable_path,
                )
                return

        cls.process = subprocess.Popen(
            [executable_path, "server", "-host", "localhost", "-port", "0"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        line = cls.process.stdout.readline().decode("utf-8")
        try:
            cls.infos = json.loads(line)
        except ValueError as e:
            sublime.error_message(
                "Failed to start jsoncomma server.\n\n{}\n\nMore details in the console",
                e,
            )
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

        sublime.status_message(
            "JSONComma: server started on {}".format(server.infos["addr"])
        )

    @classmethod
    def stop(cls):
        """ stops the server

        First, try to terminate the server (SIGTERM), waiting (block) for 1
        second at most. If it doesn't shutdown in that time, then SIGKILL is
        sent.

        On windows, process.terminate() is equivalent to process.kill()
        """

        if cls.process is None:
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
        server.assert_ready()

        try:
            resp = requests.post("http://" + server.infos["addr"], data=json_to_fix)
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

    @classmethod
    def download(cls):
        """ install the binary in the right location, and store in settings.
        It returns the location of the binary. """

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
            "os x": "~/Library/Application Support/jsoncomma/jsoncomma",
        }

        notify("getting last release...")
        # get the latest version
        resp = requests.get("https://api.github.com/repos/jsoncomma/jsoncomma/releases")
        assert (
            resp.status_code == 200
        ), "[getting last release] expected 200 status code, got {}".format(
            resp.status_code
        )

        tag_name = None
        releases = resp.json()
        for release in releases:
            # ignore prereleases and drafts
            if release["draft"] or release["prerelease"]:
                continue
            tag_name = release["tag_name"]
            break

        download_url = (
            "https://github.com/jsoncomma/jsoncomma/releases/download/"
            "{tag_name}/jsoncomma_{tag_name}_{platform}_{arch}.tar.gz".format(
                tag_name=tag_name,
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

        notify("extracting tar...")
        with open(executable_path, "wb") as target, tarfile.open(
            mode="r:gz", fileobj=io.BytesIO(resp.content)
        ) as tar:

            for tarinfo in tar.getmembers():
                if tarinfo.name.startswith("jsoncomma"):
                    break

            notify("extracting file {}...", tarinfo.name)

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

        # FIXME: maybe we should have a platform dependent settings file...
        return executable_path


def confirm_automatic_download(current_path):
    # I'm not sure how I can make it clear that this is a one time thing.
    # if the user wants to update the server, he will have to do so manually
    return sublime.ok_cancel_dialog(
        "The jsoncomma server was not found at {}. ".format(current_path)
        + "However, it needs to be installed for JSONComma to work. More "
        "details can be found at https://jsoncomma.github.io"
        "\n\n"
        "Do you want JSONComma to install it for you?"
    )


def notify(format, *args, **kwargs):
    message = "JSONComma: " + format.format(*args, **kwargs)
    print(message)
    sublime.status_message(message)
