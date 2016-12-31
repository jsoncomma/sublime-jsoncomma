"""

Removes unwanted commas, and add needed ones

By math2001

"""

import sublime
import sublime_plugin
import os
import difflib

class JsonCommaCommand(sublime_plugin.TextCommand):

    """
    fix json trailing comma.
    """

    def remove_trailing_commas(self, edit):
        v = self.view
        if 'json' not in v.settings().get('syntax').lower():
            return
        regions = v.find_all(r',\s*[\]\}]')
        selection = v.sel()
        selection.clear()

        for region in regions:
            if 'punctuation' not in v.scope_name(region.begin()):
                continue
            selection.add(region)

        v.run_command('move', {"by": "characters", "forward": False})
        v.run_command('right_delete')

    def add_needed_comma(self, edit):
        v = self.view
        region = False
        while region is not None:
            region = v.find(r'[\}\]"]\s*(//[^\n]*\s*)*(/\*(.|\n)*\*/\s*)*\s*["\{\[]',
                            region.begin() + 1 if region else 0)
            if region is None or (region.begin() == -1 and region.end() == -1):
                region = None
                continue
            if not 'punctuation' in v.scope_name(region.begin()):
                continue
            if (v.substr(region.begin()) == '"' and 'punctuation.definition.'
                'string.end.json' not in v.scope_name(region.begin()) ):
                continue
            text = v.substr(region)
            v.replace(edit, region, text[0] + ',' + text[1:])

    def run(self, edit):
        v = self.view
        initial_colrows = []
        for region in v.sel():
            initial_colrows.append(v.rowcol(region.begin()))

        self.add_needed_comma(edit)
        self.remove_trailing_commas(edit)

        v.sel().clear()
        for col, row in initial_colrows:
            line_length = len(v.substr(v.line(sublime.Region(v.text_point(col, 0)))))
            if row > line_length:
                row = line_length
            v.sel().add(sublime.Region(v.text_point(col, row)))

    def is_enabled(self):
        return True
        return 'json' in self.view.settings().get('syntax').lower()

class JsonCommaListener(sublime_plugin.EventListener):

    def on_pre_save(self, view):
        if view.settings().get('jsoncomma_on_save', False) is True:
            view.run_command('json_comma')

class JsonCommaTestCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        v = self.view
        if v.size() > 0:
            return sublime.error_message("JSONComma tests are, for global "
                                         "performance reasons, going to use "
                                         "the current view. Please create a"
                                         "new empty one. (File -> New File)")

        tests_dir = os.path.join(os.path.dirname(__file__), 'tests')
        nb_tests, fails = 0, []
        for item in os.listdir(tests_dir):
            nb_tests += 1
            with open(os.path.join(tests_dir, item)) as fp:
                content = fp.read()

            base, expected = content.split('--- RESULT ---\n')
            v.insert(edit, 0, base)
            v.settings().set('syntax',
                                     'Packages/JavaScript/JSON.sublime-syntax')
            JsonCommaCommand(v).run(edit)
            actual = v.substr(sublime.Region(0, v.size()))

            if actual != expected:
                diff = difflib.ndiff(actual.splitlines(keepends=True),
                                     expected.splitlines(keepends=True))
                diff = list(filter(lambda line: not line.startswith('?'),
                                   diff))
                diff = ''.join(diff)
                fails.append(diff)

        answer = ["JSONCommaTestr"]
        answer.append("=" * len(answer[-1]))
        answer.append('')
        answer.append('On {} test{}, {} '
                      'failed'.format(nb_tests,
                                      's' if nb_tests > 1 else '',
                                      len(fails)))
        if len(fails) > 0:
            answer.append('Fails')
            answer.append('-' * len(answer[-1]))
            for fail in fails:
                answer.append(fail)
        v.erase(edit, sublime.Region(0, self.view.size()))
        v.insert(edit, 0, '\n'.join(answer))
