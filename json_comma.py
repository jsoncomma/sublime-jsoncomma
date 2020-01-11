import sublime
import sublime_plugin
from functools import lru_cache
from .server import server, notify

SETTING_VIEW_ENABLED = "jsoncomma_enabled"


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
    # FIXME: is there a cheap way to support .tmLanguage files?
    # there is going to be fewer and fewer of them anyway...
    if not syntax.endswith(".sublime-syntax"):
        return ""

    content = sublime.load_resource(syntax)
    for i, line in enumerate(content.splitlines()):
        # assume it's somewhat decently formated. No people going `name  :`
        # for example
        if line.startswith("name:") or line.startswith("name :"):
            return line

    # none of the lines contain a the text "name: ".
    # it's weird that it is even allowed to be a syntax...
    return ""


def plugin_loaded():
    # start async because server.start might download jsoncomma synchronously
    # (ie. it would block the editor)
    sublime.set_timeout_async(server.start, 0)


def plugin_unloaded():
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
        self.view.run_command("jsoncomma_fix", {"ranges": [(0, self.view.size())]})


class JsoncommaFixCommand(sublime_plugin.TextCommand):
    def run(self, edit, ranges=None):
        try:
            server.assert_ready()
        except AssertionError as e:
            notify("couldn't fix {}: {}", self.view.file_name(), e.args[0])

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
