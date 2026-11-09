// Run each slide source of one deck against PptxGenJS, one slide to a file.
//
//   node runner.js <job.json>
//
// `lab_deck/build.py` writes the job and sets NODE_PATH so `require("pptxgenjs")` finds the
// conda package. A slide source is a CommonJS module that exports `(slide, deck) => {}`. It
// requires nothing from here: everything it needs arrives on `deck`.
//
// Every slide gets a presentation of its own, so a slide's shape ids depend on that slide's
// source alone. `lab_deck/merge.py` puts the one-slide files together.
"use strict";

const fs = require("fs");
const path = require("path");
const PptxGenJS = require("pptxgenjs");

const job = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));

// 16:9, PowerPoint's own widescreen size, in inches.
const W = 13.333;
const H = 7.5;
const MARGIN = 0.7;
const BLACK = "000000";
const WHITE = "FFFFFF";
// The page number's box, in the bottom margin, clear of anything a slide draws inside it.
const PAGE = { x: W - MARGIN - 1, y: H - 0.5, w: 1, h: 0.3 };

// The helpers a slide source draws with, bound to the presentation its slide belongs to.
function helpers(pres) {
  const deck = {
    pres,
    W,
    H,
    margin: MARGIN,
    font: job.theme.font,
    accent: job.theme.accent,
    text: BLACK,
    size: job.size,

    // The path of a picture in the deck folder's pictures/.
    picture(name) {
      return path.join(job.pictures, name);
    },

    // The slide's conclusion, top left, two lines at most.
    title(slide, text) {
      slide.addText(text, {
        x: MARGIN, y: 0.4, w: W - 2 * MARGIN, h: 1.2,
        fontFace: deck.font, fontSize: deck.size.title, bold: true, color: BLACK,
        margin: 0, valign: "top", objectName: "Slide title",
      });
    },

    // Phrases, one per line. An item is a string or { text, accent, bold }.
    lines(slide, items, box = {}) {
      const runs = items.map((item) => {
        const it = typeof item === "string" ? { text: item } : item;
        return {
          text: it.text,
          options: { color: it.accent ? deck.accent : BLACK, bold: Boolean(it.bold), breakLine: true },
        };
      });
      slide.addText(runs, {
        x: MARGIN, y: 1.9, w: W - 2 * MARGIN, h: H - 1.9 - MARGIN, ...box,
        fontFace: deck.font, fontSize: box.fontSize || deck.size.body,
        margin: 0, valign: "top", paraSpaceAfter: 8,
      });
    },

    // A table: rows of cells, the first row its header. A cell is a string or
    // { text, accent, bold }. Hairlines between rows only, and no fill.
    table(slide, rows, box = {}) {
      const { fontSize, ...place } = box;
      const cells = rows.map((row, r) => row.map((cell) => {
        const it = typeof cell === "string" ? { text: cell } : cell;
        return {
          text: it.text,
          options: { color: it.accent ? deck.accent : BLACK, bold: r === 0 || Boolean(it.bold) },
        };
      }));
      const line = { type: "solid", pt: 0.75, color: BLACK };
      const none = { type: "none" };
      slide.addTable(cells, {
        x: MARGIN, y: 1.9, w: W - 2 * MARGIN, ...place,
        fontFace: deck.font, fontSize: fontSize || deck.size.floor, color: BLACK,
        border: [none, none, line, none], valign: "middle", objectName: "Table",
      });
    },
  };
  return deck;
}

// The page number: a plain text box, drawn last so that it sits on top and takes the id after
// the slide's own shapes. Not PptxGenJS's `slideNumber`, which is PowerPoint's field with one
// fixed shape id on every slide.
function number(slide, deck, page) {
  slide.addText(String(page), {
    ...PAGE,
    fontFace: deck.font, fontSize: deck.size.citation, color: BLACK,
    align: "right", valign: "bottom", margin: 0, objectName: "Page number",
  });
}

async function build({ id, source, output, page }) {
  const pres = new PptxGenJS();
  pres.layout = "LAYOUT_WIDE";
  pres.title = job.title;
  pres.theme = { headFontFace: job.theme.font, bodyFontFace: job.theme.font };
  const deck = helpers(pres);
  const slide = pres.addSlide();
  slide.background = { color: WHITE };
  try {
    const draw = require(source);
    if (typeof draw !== "function") {
      throw new Error("the file must export a function: module.exports = (slide, deck) => {}");
    }
    await draw(slide, deck);
    if (page !== null) number(slide, deck, page);
    await pres.writeFile({ fileName: output });
  } catch (error) {
    console.error(`slide ${id} (slides/${id}.js): ${error.message}`);
    process.exit(1);
  }
}

(async () => {
  for (const slide of job.slides) await build(slide);
})();
