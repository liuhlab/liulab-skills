# The round trip

How a hand edit made in PowerPoint gets into the slide sources, so that the next build keeps
it. Open this page when the user has edited the built deck, or before you rebuild a deck the
user may have opened or still has open.

The built deck is an output. A rebuild writes it again from the slide sources, so an edit
that lives only in the deck file is lost at the next build. Never revert a hand edit: copy it
into the source.

## Steps

1. **Commit before you touch the deck.** In the deck folder, commit the deck file as the user
   handed it back. The hand edits are then in history whatever happens next.
2. **Compare.** Run `lab-deck compare [<folder>]`. It lists every edit since the last build,
   slide by slide and shape by shape. It reports only, and writes no file itself. If it says
   it saved the deck in PowerPoint, tell the user and commit the deck again: that commit is
   the one step 5 names.
3. **Copy each edit into the slide source.** One edit at a time, in `slides/<id>.js` for the
   slide the report names. A reorder goes in `slides` in `deck.toml`. A slide added by hand
   gets a new source and a new id; a deleted slide loses its id in `deck.toml`. Tell the user
   about any edit you cannot write in a source. Never drop one in silence.
4. **Rebuild over the main deck.** Run `lab-deck build`. There is one deck file: never build
   to a second name beside it. Options for a slide are built in a scratch copy outside the
   deck folder, which is then deleted: [build.md](build.md#options-for-one-slide). If it says it closed and reopened the deck, tell the user.
   `build` refuses to replace a deck that was saved by hand and is not committed as it is:
   commit it, and start again at step 2. Over a committed one it builds, and prints the
   commit that step 5 names.
5. **Check the rebuild kept the edits.** Run `lab-deck compare --since <commit of step 1>`.
   It compares the new build with the hand-edited deck, and should list nothing. What it
   lists is an edit the sources still lack, read backwards: "was" is the user's deck.
6. **Commit after the build.**

If the deck folder has a build README, it holds the current state only: what the deck is and
how to build it. The history of builds and hand edits is in git, never in a log in that file.

## A deck left open in PowerPoint

The user need not close the deck first. On a Mac, `compare` and `build` ask PowerPoint
whether it has the deck open. They never look for a lock file.

| The deck is | `lab-deck compare` | `lab-deck build` |
| --- | --- | --- |
| Not open, or PowerPoint is not running | Reads the file | Writes the file |
| Open and saved | Reads the file | Closes the deck, writes it, reopens it at the slide that was showing, and says so |
| Open with unsaved changes | Has PowerPoint save it, says so, then reads the file | Refuses, because a build would lose those changes. Run `compare` first |
| Not shown to be closed | Stops | Stops |

PowerPoint is never started to be asked. It saves the deck in place only. The other decks
open in it are left alone. If the build fails after the close, the last built deck is
reopened. Pass on to the user every line that says what was saved, closed or reopened.

**The stop.** Off a Mac, when macOS denies permission, or when PowerPoint refuses or does
not answer in 30 seconds, the command stops and has read and written nothing. Ask the user
to save the deck and close it in PowerPoint. When they say it is done, run the command again
with `--closed`. `--closed` is the user's word and covers only a PowerPoint that cannot be
asked: if PowerPoint answers that the deck is open, its answer wins. Never pass `--closed`
before the user has said so. A dialog left open in PowerPoint also blocks it: ask the user
to answer the dialog.

**The permission prompt.** The first time an agent program runs either command with
PowerPoint running, macOS asks once whether that program may control Microsoft PowerPoint.
Tell the user to expect it and to click OK. Each agent program gets its own prompt. After a
"Don't Allow", the commands stop as above; the user turns the permission back on in System
Settings, under Privacy & Security, Automation.

## The report

```text
slide data (page 3)
  shape 4 "Text 1" (shape): text changed
      was "Below the table"
      now "Under the table"
```

A slide is named by its id, which is its source file's name, and by its page in the deck as
it is now. A shape is named by its shape id and its name. The nth thing a source draws has
shape id n + 1, so the id finds the call in the source. Places and sizes are in inches, as a
source gives them. An added shape is described in full, to write it from.

| Kind | Means |
| --- | --- |
| `text changed` | The words of a text box or of a table cell, named by row and column |
| `moved`, `resized`, `rotated` | The place, the size, the rotation or a flip |
| `style changed` | Words that both texts hold are compared, word by word. Font, size, bold, italic, underline, colour, alignment, bullet, level and vertical anchor of text; fill, outline and preset geometry of a shape; the file and crop of a picture; the rows, columns and column widths of a table |
| `renamed` | The shape's name in the selection pane |
| `added`, `deleted` | A shape, a group or a slide. A group made by hand is `added`, and the shapes inside it are not moved |
| `reordered` | The order of the slides |
| `hidden`, `shown again` | A slide hidden in PowerPoint, or a hidden slide shown |

## What compare cannot see yet

Check these by eye, and ask the user when unsure:

- animations and slide transitions
- speaker notes
- the order shapes are drawn in, front to back
- the slide background, the master, the layouts and the theme
- the height of a table and of its rows, and the borders and fills of its cells
- shadows and other effects, transparency, gradient stops and arrowheads
- text insets, autofit, line spacing and paragraph spacing
- hyperlinks and alt text
- the picture adjustments: brightness, recolour, compression
- the points of a freeform shape, and what is inside a chart or a SmartArt

The command prints this list with every report.

## Known issue: a saved deck is not a build

PowerPoint rewrites the whole file when it saves, so a deck saved with no edit still differs
from a fresh build, byte for byte and in git. These differences are not edits, and `compare`
ignores them:

- the order and spelling of the XML, and the ids PowerPoint gives new parts
- how PowerPoint splits one line of text into runs
- the language, spelling and revision marks on text
- the file's properties, thumbnail, view settings and saved times
- the digits of a page number, which the build writes again
- the height PowerPoint gives a table's rows when it lays the table out

So after a save, `git status` shows the deck as changed even when `compare` finds no edit.
Trust `compare` for the kinds it reads, and your eyes for the list above.

## How the last build is found

A build writes one fixed time, 1980-01-01, into the deck file, and a save in PowerPoint
replaces it. `compare` walks the commits that changed the deck file, newest first, and takes
the first whose deck still has that time. So step 1 does not hide the build behind it.

`compare` refuses when no commit holds a build. Commit after every build. When the last
build is known but not found, name it: `lab-deck compare --since <commit>`.

A slide is matched by its id inside the file and a shape by its shape id. PowerPoint keeps
both. A slide copied in PowerPoint carries the id of the slide it was copied from, and is
reported as added.
