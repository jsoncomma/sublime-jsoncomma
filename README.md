# JSONComma

JSONComma is a really simple but helpful plugin that, as it's name says, helps managing those damn commas in json.

<!-- MarkdownTOC -->

- [Examples:](#examples)
    - [It removes trailling comma](#it-removes-trailling-comma)
    - [Adds **needed** commas!](#adds-needed-commas)
    - [Supports comments](#supports-comments)
    - [Everything mixed up](#everything-mixed-up)
- [Usage](#usage)
    - [Run the command \(`json_comma`\)](#run-the-command-json_comma)
    - [You want to run this as soon as you save?](#you-want-to-run-this-as-soon-as-you-save)
- [Installation](#installation)
    - [Using package control](#using-package-control)
    - [Using the command line](#using-the-command-line)
- [Contributing](#contributing)

<!-- /MarkdownTOC -->


## Examples:

### It removes trailling comma

```diff
 {
     "hello": "world",
-    "not needed": "damn comma",
+    "not needed": "damn comma"
 }
```

### Adds **needed** commas!

```diff
 {
-    "hello": "world"
-    "not needed": "damn comma"
+    "hello": "world",
+    "not needed": "damn comma",
     "aList": [
-        "hello" "world"
-        "this" "is" "a nasty ]{ example ] "
-        ["BUT" "IT" "STILL" "WORKS!!"]
+        "hello", "world",
+        "this", "is", "a nasty ]{ example ] ",
+        ["BUT", "IT", "STILL", "WORKS!!"]
     ]
 }
```

### Supports comments

```diff
 {
-    "hello": "world"
+    "hello": "world",
     // A Comment
-    "not Needed": "damn Comma" // an other
+    "not Needed": "damn Comma", // an other
     // with a second one
     "alist": [
-        "hello" "world"
-        "this" // a comment
-        "is" "a Nasty ]{ Example ] "
-        ["but" "it" "still" "works!!"]
+        "hello", "world",
+        "this", // a comment
+        "is", "a Nasty ]{ Example ] ",
+        ["but", "it", "still", "works!!"]
     ]
 }
```

### Everything mixed up

```diff
 {
-    "name": "JSONComma" // no space allowed in GitHub repository name
-    "version": "0.1.0" // wait a bit before 1.xxx to detect bugs
+    "name": "JSONComma", // no space allowed in GitHub repository name
+    "version": "0.1.0", // wait a bit before 1.xxx to detect bugs
     "labels": [
-        "json"
-        "JSON"
-        "light"
-        "on_save",
-    ],
+        "json",
+        "JSON",
+        "light",
+        "on_save"
+    ]

 }
```

## Usage

If there is no selection (to be correct, it'd be no *non-empty* selection), it will format the entire file.

### Run the command (`json_comma`)

Open up the command palette and look for `JSONComma: Run`. Hit enter, and you're done!

### You want to run this as soon as you save?

*Pas de probleme!* Add this to your settings:

```json
"jsoncomma_on_save": true
```

*Et voila!* Each time you'll save a `JSON` file (or a json-like  — [more info](#json-like)), JSONComma will be run. Enjoy! :smile:

## Installation

Because it is not available on package control for now, you have to add this repo "manually" to your list.

### Using package control

1. search for `Package Control: Install Package` in the command palette — <kbd>ctrl+shift+p</kbd> (might take a few seconds)
2. search for `JSONComma`
3. hit <kbd>enter</kbd> :wink:

### Using the command line

```bash
cd "%APPDATA%\Sublime Text 3\Packages"             # on window
cd ~/Library/Application\ Support/Sublime\ Text\ 3 # on mac
cd ~/.config/sublime-text-3                        # on linux

git clone "https://github.com/math2001/JSONComma"
```

> Which solution do I choose?

It depends of your needs:

- If you intend to just use JSONComma, then pick the first solution (Package Control), **you'll get automatic update**.
- On the opposite side, if you want to tweak it, use the second solution. Note that, to get updates, you'll have to `git pull`

## Contributing

First, you can raise an issue to let me know the bug you've found, the improvement you're thought of, etc... Always raise an issue before you PR me.

If you want to solve this bug/add your feature yourself, here's what I'd like you to do:

- create a new branch `your-feature-name`
- add your feature
- run the tests (see bellow). **They must pass**.
- push and PR me!

#### How to run the test

If you have a look at the code, you'll see that there is a command `json_comma_test`, but it is shown nowhere. It is *wanted*. The final user doesn't care about the test command. So, *it is your job to add it to the command palette, bind it to a shortcut, or if you like to complicate your life, run it from the console* :smile:

Run the command, a new file will popup and automatically close itself straight away. JSONComma needs a file to run the test because it uses the scope names to detect if it needs to add/remove a comma.

The result will be shown it an output panel though.
