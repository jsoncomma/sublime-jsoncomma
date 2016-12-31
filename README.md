# JSONComma

JSONComma is a really simple but helpful plugin that, as it's name says, helps managing those damn commas in json.

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

## Supports inline comments

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

## Installation

Because it is not available on package control for now, you have to add this repo "manually" to your list.

#### Using package control

1. Open up the command palette (`ctrl+shift+p`), and find `Package Control: Add Repository`. Then enter the URL of this repo: `https://github.com/math2001/JSONComma` in the input field.
2. Open up the command palette again and find `Package Control: Install Package`, and just search for `JSONComma`. (just a normal install)

#### Using the command line

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

### Run the command (`json_comma`)

Open up the command palette and look for `JSONComma: Run`. Hit enter, and you're done!

### You want to run this as soon as you save?

*Pas de probleme!* Add this to your settings:

```json
"jsoncomma_on_save": true
```

*Et voila!* Each time you'll save a `JSON` file, JSONComma will be run. Enjoy! :smile:
