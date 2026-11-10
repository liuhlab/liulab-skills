# Checking a deck: the render and the lint

Two commands check a built deck. `lab-deck render` makes the pictures the agent looks at.
`lab-deck lint` checks the slide rules a script can check; `lab-deck build` runs it too.
The build itself is in [build.md](build.md).

## Render

`lab-deck render` writes one PNG per click state into `renders/` in the deck folder, hidden
slides included. Git ignores that folder. Run it after every build.

A picture's name is `<slide id>.click<n>.png`: `click0` is the slide as it opens, and
`click<n>` is the slide after n clicks. The name holds no page number, so each picture is
compared with the last picture of the same slide and click state.

The command prints one line per picture to look at:

| Line | Means |
| --- | --- |
| `new: renders/<name>` | The click state had no picture before |
| `changed: renders/<name>` | The picture differs from the last render's |
| `gone: renders/<name>` | No slide has this click state now. The picture was deleted |

Look at each `new` and `changed` picture. A slide that moves to another page is listed as
changed, because its page number changed.

How it works, and its limits:

- The deck is only read. The command writes a scratch copy with one plain slide per click
  state, LibreOffice converts the copy to a PDF, and Poppler's `pdftoppm` makes the PNGs.
- LibreOffice is the system's app, found as `soffice` on PATH or inside the Mac app. Poppler
  comes with the plugin's pixi environment. Run `lab-deck preflight` when either is missing.
- On a Mac, LibreOffice has aborted inside a command sandbox. When the render fails that
  way, run it again outside the sandbox.
- LibreOffice draws a missing font with another one, and the text then wraps elsewhere.
  `lab-deck preflight` says whether the theme's font is installed.
- A picture shows Appear and Disappear only. For any other effect, such as one added by hand
  in PowerPoint, the command warns and names the slide.
- LibreOffice is not PowerPoint. It accepts a file that PowerPoint offers to repair, so the
  user still opens the deck in PowerPoint once at the end.

## The lint

`lab-deck lint` reads the built deck and the brief's room, in about a second, with no model.
`lab-deck build` runs the same checks on the deck it is about to write. A blocking failure
stops the build and leaves the last built deck as it was. Fix the slide source, never the
check.

| Check | Slide rule | Fails when |
| --- | --- | --- |
| `size-floor` | 8 | Text is under the room's floor: 20 pt in a meeting room, 24 pt in a hall |
| `text-overflow` | 8 | Text takes more height than its box has |
| `picture-over-text` | 16 | A picture is drawn over text, in a click state that shows both |
| `negative-size` | 17 | A shape's width or height is under zero |
| `click-cues` | 18 | A slide's notes do not carry one `[Click]` cue per click |

Each failure names the slide by id and page number, the shape, the check and the rule:

```text
slide results (page 3), shape "Text 1": size-floor (rule 8): "Too small" is 16 pt, under the 20 pt floor
```

- **The size floor** holds for every run of text, table cells included, Chinese as Latin. The
  shape named `Page number` is exempt. The shape named `Citation` may be 12 pt: one per
  slide, on one line. Draw it with `deck.citation(slide, "Author, Journal, year")`. Any other
  12 pt text fails. A raw `slide.addText` with no `fontSize` is 18 pt and fails: pass
  `fontSize: deck.size.body`.
- **Overflow is an estimate.** The lint sums the glyph widths of the deck's font from its
  font file, wraps the lines and compares the height with the box. With no font file on the
  machine it uses Helvetica's widths, which Arial shares, and the report says so. A
  full-width character, Chinese included, counts as wide as the font size, and a line may
  break beside it. The lint allows 5% over the box before it fails. It does not estimate a
  table, because a table grows its rows. The pictures of the click states are the final word.
- **A picture covers text** when it is drawn after the text and over the place the lint
  estimates for the words, not over the empty part of the text's box.
- **Click cues** are checked only on a slide whose notes hold text.
