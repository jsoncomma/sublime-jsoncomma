"""

Removes unwanted commas, and add needed ones

By math2001

"""

import sublime
import sublime_plugin
import os
import difflib

def any_(iterable, key, *args):
    for item in iterable:
        if key(item, *args):
            return True
    return False

DEBUG = False

class JsonCommaCommand(sublime_plugin.TextCommand):

    """
    fix json trailing comma and add needed ones
    """

    # used to replace only in current selections
    allowed = lambda allowed_region, region: (
                allowed_region.empty() or sublime.Region(
                                   allowed_region.begin() - 1,
                                   allowed_region.end() + 1).contains(region))

    def remove_trailing_commas(self, edit, regions):
        v = self.view
        start, end = 0, None
        if regions is not None:
            start = min(regions, key=lambda region: region.begin()).begin()
            end = max(regions, key=lambda region: region.end()).end()
        region = sublime.Region(start)

        while region is not None and not region.begin() == region.end() == -1:

            region = v.find(r',((\s*//[^\n]*)*\n)?\s*[\]\}]', region.begin() + 1)
            if regions is not None:
                if region.end() > end:
                    return
                if not any_(regions, JsonCommaCommand.allowed, region):
                    continue
            if ('punctuation' not in v.scope_name(region.begin()) or
               (v.substr(region.begin()) == '"' and 'punctuation.definition.'
                'string.end.json' not in v.scope_name(region.begin()))):
                continue
            v.replace(edit, region, v.substr(region)[1:])

    def add_needed_comma(self, edit, regions=None):
        v = self.view
        start, end = 0, None
        if regions is not None:
            start = min(regions, key=lambda region: region.begin()).begin()
            end = max(regions, key=lambda region: region.end()).end()
        region = sublime.Region(start)

        while region is not None:
            region = v.find(r'[\}\]"el]\s*(//[^\n]*\s*)*\s*["\{\[]',
                            region.begin() + 1 if region else 0)

            if region is None or region.begin() == region.end() == -1:
                region = None
                continue

            if regions is not None:
                if region.end() > end:
                    return
                if not any_(regions, JsonCommaCommand.allowed, region):
                    continue

            scope = v.scope_name(region.begin())
            if not 'punctuation' in scope and not 'constant.language' in scope:
                continue
            if (v.substr(region.begin()) == '"' and 'punctuation.definition.'
                'string.end.json' not in scope):
                continue

            text = v.substr(region)
            v.replace(edit, region, text[0] + ',' + text[1:])

    def run(self, edit):
        v = self.view
        initial_colrows = []
        sels = v.sel()
        has_non_empty_region = False
        for region in sels:
            initial_colrows.append(v.rowcol(region.begin()))
            if not region.empty():
                has_non_empty_region = True

        self.add_needed_comma(edit, sels if has_non_empty_region else None)
        self.remove_trailing_commas(edit, sels if has_non_empty_region else None)

        sels.clear()
        for col, row in initial_colrows:
            line_length = len(v.substr(v.line(sublime.Region(v.text_point(col, 0)))))
            if row > line_length:
                row = line_length
            sels.add(sublime.Region(v.text_point(col, row)))

    def is_enabled(self):
        return 'json' in self.view.scope_name(self.view.sel()[0].begin())

class JsonCommaListener(sublime_plugin.EventListener):

    def on_pre_save(self, view):
        if view.settings().get('jsoncomma_on_save', False) is True:
            return
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
        v.assign_syntax('Packages/Diff/Diff.sublime-syntax')
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
            test_view.assign_syntax('Packages/JavaScript/JSON.sublime-syntax')
            test_view.run_command('json_comma')
            actual = test_view.substr(sublime.Region(0, test_view.size()))

            if actual != expected:
                diff = difflib.ndiff(expected.splitlines(keepends=True),
                                     actual.splitlines(keepends=True))
                diff = ''.join(diff)
                fails.append((item, diff))
            test_view.erase(edit, sublime.Region(0, self.view.size()))
        sublime.set_timeout_async(lambda:self.window.run_command('close'), 500)

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
            answer += ['', '- expected', '+ actual', '']
            for fail in fails:
                answer += ['',
                           '@@ ' + fail[0] + ' @@',
                           fail[1]]
        v.insert(edit, 0, '\n'.join(answer))

    def is_visible(self):
        return DEBUG
