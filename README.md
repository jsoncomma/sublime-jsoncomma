# JSONComma

This is the official plugin adapting [`jsoncomma`][] to Sublime Text 3. 

> `jsoncomma` is a simple utility which manages the commas in your JSON-like files. It adds needed ones, and removes the others.

## Settings

JSONComma will run every time you save a json-like file. It tries to be smart about what is JSON like (more details in the `should_be_enabled` function). However, you can explicitly choose whether it should fix your file on save by changing the *view* setting like so:

```json
{
    "jsoncomma_enabled": false
}
```

So, for example, if you want to disable running on save for all `.json` file, you can open a JSON file and search up in the command palette `Preferences: Settings Syntax Specific` and add the text above. This will *explicitly* disable running *on save*.

Similarly, you can explicitly *enable* it for any syntax you want. All it takes a view settings.

If JSONComma is disabled for the current view (as in it won't run on save), you can fix up some specific text by selecting it and searching up in the command palette `JSONComma: Fix Selection`.

## Note about naming

In general, you should refer to jsoncomma all in lower case. It's just that this plugin for Sublime Text has upper case letters to fit with the editor's style.

[`jsoncomma`]: http://jsoncomma.github.io