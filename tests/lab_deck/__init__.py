"""Unit tests for `src/lab_deck`, the deck build.

Each test runs `lab-deck` at its command line on a small deck folder in a temporary directory
and reads what a person would: the folder, the written deck, the message and the exit status.
The build runs the real Node.js and PptxGenJS from the pixi environment. PowerPoint is never
started; whether it opens a deck with no Repair dialog is checked by hand.
"""
