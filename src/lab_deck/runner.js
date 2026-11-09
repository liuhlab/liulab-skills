// Run each slide source of one deck against PptxGenJS and write the deck.
//
//   node runner.js <job.json>
//
// `lab_deck/build.py` writes the job and sets NODE_PATH so `require("pptxgenjs")` finds the
// conda package. A slide source is a CommonJS module that exports `(slide, deck) => {}`. It
// requires nothing from here: everything it needs arrives on `deck`.
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

const pres = new PptxGenJS();
pres.layout = "LAYOUT_WIDE";
pres.title = job.title;

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
};

for (const { id, source } of job.slides) {
  const slide = pres.addSlide();
  slide.background = { color: WHITE };
  try {
    const draw = require(source);
    if (typeof draw !== "function") {
      throw new Error("the file must export a function: module.exports = (slide, deck) => {}");
    }
    draw(slide, deck);
  } catch (error) {
    console.error(`slide ${id} (slides/${id}.js): ${error.message}`);
    process.exit(1);
  }
}

pres.writeFile({ fileName: job.output }).catch((error) => {
  console.error(`writing the deck: ${error.message}`);
  process.exit(1);
});
