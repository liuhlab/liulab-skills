# The build

How a deck folder becomes a PowerPoint file. Open this page at step 3, before you write a
slide source or run `lab-deck`.

`lab-deck` ships with the plugin and is on the PATH after `/lab-setup`. The build code lives
in the plugin, never in a deck folder (`docs/adr/0018-the-deck-build-ships-with-the-plugin.md`).

## Commands

| Command | Does |
| --- | --- |
| `lab-deck new <folder> [--title <title>]` | Makes a deck folder with one starter slide and a local git repo. Warns when the folder is inside a synced cloud folder, and changes nothing for it |
| `lab-deck build [<folder>]` | Builds the deck folder, by default the current one, into its PowerPoint file |
| `lab-deck compare [<folder>] [--since <commit>]` | Lists the hand edits in the deck since its last build, and writes no file itself: [round-trip.md](round-trip.md) |

A deck left open in PowerPoint is handled by both `build` and `compare`, and both take
`--closed`: see "A deck left open in PowerPoint" in [round-trip.md](round-trip.md). Off a
Mac, a rebuild over an existing deck stops until the user has saved and closed it.

Exit codes: 0 fine, 1 refused with the reason on stderr, 2 wrong usage.

## The deck folder

| Path | Holds |
| --- | --- |
| `brief.toml` | The audience brief: `audience`, `knows`, `minutes`, `language`, `known_terms`, `room`, `use` |
| `deck.toml` | `title`, `output` (the built file's name) and `slides`, the slide ids in the order shown |
| `theme.toml` | `font` and `accent`, and nothing else |
| `slides/<id>.js` | One source file per slide. The file name is the slide's id |
| `pictures/` | Pictures, each with the prompt that made it beside it |
| `notes/<id>.md` | The speaker notes of the slide with that id |
| `<output>` | The built deck |

A slide's id is a name, never a number: letters, digits, `-`, `_` and `.`. To insert a slide,
write `slides/<new id>.js` and add the id to `slides` in `deck.toml` at its place. Rename
nothing. To reorder, move ids in the list. To drop a slide, remove its id.

`room` in the brief sets the sizes: `"meeting room"` gives 24 pt body text and a 20 pt floor,
`"hall"` gives 28 pt and 24 pt. A missing room means a meeting room.

The theme is a white background, Arial, black text and one accent colour, blue `0072B2`.
`theme.toml` may change `font` and `accent`. The build refuses any other key.

## A slide source

```js
module.exports = (slide, deck) => {
  deck.title(slide, "Trimming raises the alignment rate in every sample");
  deck.lines(slide, ["Trimmed reads: higher rate", { text: "About 80%", accent: true }]);
};
```

`slide` is the PptxGenJS slide, so every PptxGenJS call works on it. `deck` carries the house
style. A source requires nothing: no `require("pptxgenjs")`, no path to the build.

| On `deck` | Is |
| --- | --- |
| `title(slide, text)` | The slide's conclusion, top left, bold |
| `lines(slide, items, box)` | Phrases, one per line. An item is a string or `{ text, accent, bold }` |
| `table(slide, rows, box)` | A table. The first row is the header. A cell is a string or `{ text, accent, bold }` |
| `picture(name)` | The path of a file in `pictures/`, for `slide.addImage({ path })` |
| `group(slide, name, draw)` | What `draw()` draws becomes one group named `name` |
| `section(slide, name, draw)` | What `draw()` draws is one section: a click shows or hides all of it |
| `click(slide, { appear, disappear })` | One click. Each key takes a section name or a list of them |
| `font`, `accent`, `text` | The theme's font, its accent colour and black |
| `size` | `title`, `body`, `floor` and `citation`, in points, for the brief's room |
| `W`, `H`, `margin` | 13.333 by 7.5 inches, and the 0.7 inch margin |
| `pres` | The PptxGenJS presentation, for `deck.pres.ShapeType` |

`box` overrides the place: `{ x, y, w, h, fontSize }`, in inches and points. Pass `fontFace:
deck.font` on every raw `addText` and `addTable`. Give a shape that a later step must find an
`objectName`.

## Groups, sections and clicks

```js
module.exports = (slide, deck) => {
  deck.title(slide, "Trimming raises the alignment rate in every sample");
  deck.section(slide, "before", () => {
    deck.lines(slide, ["Untrimmed reads"], { h: 1 });
  });
  deck.section(slide, "after", () => {
    deck.group(slide, "Rate chart", () => {
      // every slide.addShape of the drawing
    });
    deck.lines(slide, ["Trimmed reads"], { y: 6, h: 1 });
  });
  deck.click(slide, { appear: "after", disappear: "before" });
};
```

- **Group every drawing made of several shapes**, so it moves and reveals as one. A group
  holds shapes only: no group and no section inside it.
- **A section is everything one `draw()` draws.** Draw a section after the one before it,
  never inside it. A group may sit inside a section.
- **Each `deck.click` call is one click, in call order.** Its effects are PowerPoint's Appear
  and Disappear and nothing else. A section that appears is hidden when the slide opens.
  What no click names is always shown.
- A click names a section, or a group outside any section. It never names a shape id, so a
  drawing call that moves stays in the section it is written in, and every click stays right.
- A slide with n clicks has n + 1 click states.

The build refuses, naming the slide: a click that names no section or group; a section or
group that a second click names, because PowerPoint plays one effect per object; a name used
twice; a section or group that draws nothing; a click on a group inside a section; a click on
a section that holds the title.

To read the clicks of a built deck, call `lab_deck.stage.read(path)`. It returns, for each
slide id, one list per click of the objects shown or hidden: shape id, name and `appear`,
`disappear` or `other`. `other` is an effect the build never writes, such as one added by
hand in PowerPoint.

## Notes

`notes/<id>.md` holds the notes of slide `<id>` as plain text. The build puts the text into
the slide's notes as written, with no Markdown turned into formatting. Start the line the
speaker says after a click with `[Click]`: one cue per click, none on a slide with no click.
A slide with no notes file gets empty notes. Never call `slide.addNotes`: the build refuses
it, because PptxGenJS counts notes as a thing drawn and every later shape id would move.

## What the build does

1. Reads the deck folder, and refuses a slide id with no source or a theme with an extra key.
2. Runs each slide source on its own, into a one-slide file with its notes. A slide's shape
   ids depend on that slide's source alone: the nth thing the source draws has id n + 1.
3. Draws the page number last on every slide but the first, as a plain text box named
   `Page number`, at the citation size in the bottom right margin. The number is the slide's
   place in the deck. The first slide is the title and has none.
4. Gives each table's frame the id its place in the drawing order gives it, and names the
   slide by its id inside the file.
5. Wraps each group's shapes in a group shape where they stand. No shape's id, place or XML
   changes. A group takes the id after the slide's highest.
6. Writes the clicks as the slide's timing: one step per click, one Appear or Disappear per
   object of each section named.
7. Merges the one-slide files in the order of `deck.toml`. Each slide's XML goes in byte for
   byte. A picture used on several slides is stored once.
8. Reads the merged file back: every part present and declared, slides in order, no two
   shapes with one id, no negative size.
9. Moves the checked file over the last built deck in one step.

A failure at any step leaves the last built deck as it was and names the slide. The same deck
folder builds to the same bytes, so a rebuild that changes nothing shows no change in git.
For that, the times inside the file are fixed at 1980-01-01.

Inserting a slide changes one thing on the slides after it: the digits of the page number.

## Known PptxGenJS limits

The build uses PptxGenJS 4.0.1. Each limit below was read in its source and holds in 3.12 too.

| Limit | What the build does |
| --- | --- |
| A table's frame is numbered by a count of tables, apart from the other shapes. The first table on a slide gets id 2, the id of the first shape, and PowerPoint offers to repair the deck | Step 4 renumbers the frame. `slide.addTable` and `deck.table` are both safe |
| `slideNumber` writes PowerPoint's slide-number field with shape id 25 on every slide, the id of the 24th shape | The build draws its own text box. Never set `slideNumber` |
| A picture with no `altText` gets its whole path on this machine as its alt text | The build writes the file's name instead. Pass `altText` to `slide.addImage` to say more |
| No group shapes and no animation | Steps 5 and 6 write them into the slide after PptxGenJS. Use `deck.group`, `deck.section` and `deck.click` |
| A video or a sound is numbered apart from the other shapes, as a table is | The build refuses a slide where two shapes share an id |
| A chart or a slide master adds parts that differ from slide to slide | The merge does not carry them, and the build refuses the slide. Show a chart as a picture |

## Where PptxGenJS comes from

`pptxgenjs` is a conda-forge package in the plugin's pixi environment. No `npm install` runs
anywhere. The package lands in `lib/node_modules` under the environment's prefix, and Node
does not search that folder by itself. `lab-deck build` sets `NODE_PATH` to it for the one
Node process it starts. Run a slide source only through `lab-deck build`: plain `node` cannot
find the library.
