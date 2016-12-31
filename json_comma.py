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
        regions = v.find_all(r'(\s*?(//[^\n]*)*)*[\]\}]')
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
        self.window = self.view.window()

        test_view = self.window.new_file()
        test_view.set_scratch(True)

        v = self.window.find_output_panel('JSON Comma Testr')
        if v is None:
            v = self.window.create_output_panel('JSON Comma Testr')
        else:
            v.erase(edit, sublime.Region(0, v.size()))
        v.settings().set('syntax', 'Packages/Diff/Diff.sublime-syntax')
        self.window.run_command('show_panel', {
            "panel": 'output.JSON Comma Testr'
        })


        tests_dir = os.path.join(os.path.dirname(__file__), 'tests')
        nb_tests, fails = 0, []
        for item in os.listdir(tests_dir):
            nb_tests += 1
            with open(os.path.join(tests_dir, item)) as fp:
                content = fp.read()

            base, expected = content.split('--- RESULT ---\n')
            test_view.insert(edit, 0, base)
            test_view.settings().set('syntax',
                                     'Packages/JavaScript/JSON.sublime-syntax')
            JsonCommaCommand(test_view).run(edit)
            actual = test_view.substr(sublime.Region(0, test_view.size()))

            if actual != expected:
                print("json_comma.py:108", expected.splitlines(keepends=True))
                diff = difflib.ndiff(expected.splitlines(keepends=True),
                                     actual.splitlines(keepends=True))
                diff = ''.join(diff)
                fails.append((item, diff))
            test_view.erase(edit, sublime.Region(0, self.view.size()))
        sublime.set_timeout_async(lambda:self.window.run_command('close'))

        answer = ["JSON Comma Testr"]
        answer.append("=" * len(answer[-1]))
        answer.append('')
        answer.append('On {} test{}, {} '
                      'failed'.format(nb_tests,
                                      's' if nb_tests > 1 else '',
                                      len(fails)))
        if len(fails) > 0:
            answer.append('')
            answer.append('Fails')
            answer.append('~' * len(answer[-1]))
            for fail in fails:
                answer += ['',
                           '@@ ' + fail[0] + ' @@',
                           fail[1]]
        v.insert(edit, 0, '\n'.join(answer))
