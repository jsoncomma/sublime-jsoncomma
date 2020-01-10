import os.path
import json
import subprocess
import sublime
import sublime_plugin
import requests
from functools import lru_cache

SETTINGS = "JSONComma.sublime-settings"
SETTINGS_EXECUTABLE = "executable_path"
SETTING_VIEW_ENABLED = "jsoncomma_enabled"


def notify(format, *args, **kwargs):
    message = "JSONComma: " + format.format(*args, **kwargs)
    print(message)
    sublime.status_message(message)


class server:
    process = None
    infos = None

    @classmethod
    def assert_ready(cls):
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

        executable = sublime.load_settings(SETTINGS).get(SETTINGS_EXECUTABLE)
        executable = os.path.expanduser(executable)

        cls.process = subprocess.Popen(
            [executable, "server", "-port", "0"],
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

    @classmethod
    def stop(cls):
        assert cls.process is not None, "no server running"
        cls.process.terminate()
        try:
            cls.process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            notify("had to kill (SIGKILL) process after 1 second timeout")
            cls.process.kill()

        cls.process = None
        cls.infos = None

    @classmethod
    def fix(cls, json_to_fix):

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


def should_be_enabled(*, filename, syntax, scope):
    assert isinstance(filename, str), "filename should be a string"
    assert isinstance(syntax, str), "syntax should be a string"
    assert isinstance(scope, str), "scope should be a string"

    # notice how this logic could be handled by the server...
    # would it make sense to outsource this? No, because
    # this behavior is editor dependent.
    return (
        "json" in syntax.lower()
        or "json" in scope.lower()
        or "json" in filename.split(".")[-1].lower()
        # this is the most expensive check, hence it's used last
        or "json" in get_syntax_name(syntax).lower()
    )


# this is quite an expensive function, and it's
# really cheap to cache (a pair of strings)
@lru_cache()
def get_syntax_name(syntax):
    content = sublime.load_resource(syntax)
    for i, line in enumerate(content.splitlines()):
        if i >= 10:
            # we look for the `name: ` line in the first 10 lines
            return False
        # assume it's somewhat decently formated. No people going `name  :`
        # for example
        if line.startswith("name:") or line.startswith("name :"):
            return line

    # there is less than 10 lines, and none of them contain a the text "name: ".
    # it's weird that it is even allowed to be a syntax...
    return False


def plugin_loaded():
    server.start()
    sublime.status_message(
        "JSONComma: server started on {}".format(server.infos["addr"])
    )


def plugin_unloaded():
    sublime.status_message("JSONCOMma: server stopped")
    server.stop()


class JsonCommaListener(sublime_plugin.ViewEventListener):
    @classmethod
    def is_applicable(cls, settings):
        explicit = settings.get(SETTING_VIEW_ENABLED)
        if explicit is False:
            return False
        elif explicit is True:
            return True

        return should_be_enabled(filename="", syntax=settings.get("syntax"), scope="")

    @classmethod
    def applies_to_primary_view_only(cls):
        return False

    def on_pre_save(self):
        try:
            server.assert_ready()
        except AssertionError as e:
            notify("couldn't fix {}, {}", self.view.file_name(), e.args[0])

        self.view.run_command("jsoncomma_fix", {"ranges": [(0, self.view.size())]})


class JsoncommaFixCommand(sublime_plugin.TextCommand):
    def run(self, edit, ranges=None):
        if ranges is not None:
            regions = (sublime.Region(*range) for range in ranges)
        else:
            regions = self.view.sel()

        for region in regions:
            self.view.replace(edit, region, server.fix(self.view.substr(region)))

    def is_enabled(self):
        has_non_empty_cell = False
        for region in self.view.sel():
            if not region.empty():
                has_non_empty_cell = True

        return has_non_empty_cell or should_be_enabled(
            filename=self.view.file_name(),
            syntax=self.view.settings().get("syntax"),
            # look at the scope at the end of the file, because it's likely that
            # it'll be where there is a line return (hence the scope will only
            # be the scope name of the general file)
            scope=self.view.scope_name(self.view.size()),
        )

    def is_visible(self):
        return self.is_enabled()
