# JSONComma

Json comma is really simple but helpful plugin that, as it's name says, helps managing those damn commas in json.

## It removes trailling comma

```diff
 {
     "hello": "world",
-    "not needed": "damn comma",
+    "not needed": "damn comma"
 }
```

## Adds **needed** commas!

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

## Installation

#### Using package control

Because it is not available on package control for now, you have to add this repo "manually" to your list.

1. open up the command palette (`ctrl+shift+p`), and find `Package Control: Add Repository`. Then enter the URL of this repo: `https://github.com/math2001/JSONComma` in the input field.
2. open up the command palette again and find `Package Control: Install Package`, and just search for `FileManager`. (just a normal install)

#### Using the command line

```bash
cd "%APPDATA%\Sublime Text 3\Packages"             # on window
cd ~/Library/Application\ Support/Sublime\ Text\ 3 # on mac
cd ~/.config/sublime-text-3                        # on linux

git clone "https://github.com/math2001/JSONComma"
```


You want to run this as soon as you save? *Pas de probleme!*

Add this to your settings:

```json
"jsoncomma_on_save": true
```

*Et voila!* Enjoy! :smile:
