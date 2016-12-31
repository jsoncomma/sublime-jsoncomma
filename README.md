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

You want to run this as soon as you save? *Pas de probleme!*

Add this to your settings:

```json
"jsoncomma_on_save": true
```

*Et voila!* Enjoy! :smile:
