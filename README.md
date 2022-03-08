
#################################################################################################

  Align Comments

#################################################################################################

This is a Sublime Text 3 plug-in to align in-line comments. The comment syntax is picked from the
<language>-Comments.tmPreferences file for the language type.

It does one of four things depending on the context:
  1.  For a single line, it creates new comments aligned to a configurable column and places the
      cursor at the end of the line ready for text to be entered.
  2.  For multiple lines, it aligns comments to the same indentation as the following non-comment
      text for comments that are indented by more than 1 character indent
  3.  For multiple lines, it aligns existing comments that are placed after some non-comment text
      to the configurable column.
  4.  Comments that have no indentation are left alone. Lines that have no comments are left alone.

These features are handy for creating consistent layout to languages that make extensive use of
in-line comments rather than comment blocks. Block and multiple selections are supported, including
all of a file.

The column is configured by setting a parameter in a sublime-settings file. This can be global or
per syntax, allowing for different values for different files. Space or tab indentations are supported.
If no column value is set, then a default column value of 80 is used. The value can be entered as
an integer number with support for text conversion built into the plug-in. If the value is invalid,
then a warning message is displayed in the console. An example of setting is:

{
  "comment_align_column": 85,
}

The command uses a default key code of <CTRL + .> (adjacent to the toggle comment command key).
The command is added to the main menu under Edit -> Comment to appear after the toggle comment
entries.

The command can be changed by adding a new entry to the Preferences -> Key Bindings - User
sublime.keymap file and editing the key combination.

[
  {"keys": ["ctrl+."], "command": "align_comment"}
]

Chris Cornish, September 2016.

