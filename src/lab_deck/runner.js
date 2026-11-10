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
//
// PptxGenJS writes no group and no animation. A source names its groups, sections and clicks
// through `deck`; the runner writes them beside the slide's file as a plan, by each one's
// place in the drawing order, and `lab_deck/stage.py` writes them into the slide.
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

// How many things the slide holds so far. PptxGenJS keeps them in one list, in drawing order.
function drawn(slide) {
  return slide._slideObjects.length;
}

function listed(names) {
  const list = typeof names === "string" ? [names] : names || [];
  if (!Array.isArray(list) || !list.every((name) => typeof name === "string")) {
    throw new Error("deck.click takes { appear, disappear }, each a name or a list of names");
  }
  return list;
}

// The helpers a slide source draws with, bound to the presentation its slide belongs to.
// `plan` collects the slide's groups, sections and clicks.
function helpers(pres, plan) {
  // The section and the group being drawn now, if any.
  const open = { section: null, group: null };

  // Run `draw`, and record what it drew under `name`, as places in the drawing order.
  function named(kind, slide, name, draw) {
    if (typeof name !== "string" || !name.trim() || typeof draw !== "function") {
      throw new Error(`deck.${kind} takes (slide, name, draw): a name and a function that draws`);
    }
    const taken = [...plan.groups, ...plan.sections].some((one) => one.name === name);
    if (taken || open.section === name || open.group === name) {
      throw new Error(`the name "${name}" is used twice; give every group and section its own name`);
    }
    if (open.group !== null) {
      throw new Error(`${kind} "${name}" is inside group "${open.group}"; a group holds shapes only`);
    }
    if (kind === "section" && open.section !== null) {
      throw new Error(`section "${name}" is inside section "${open.section}"; draw it after that one`);
    }
    const first = drawn(slide);
    open[kind] = name;
    const result = draw();
    open[kind] = null;
    if (result && typeof result.then === "function") {
      throw new Error(`${kind} "${name}": its function must draw at once, not be async`);
    }
    if (drawn(slide) === first) throw new Error(`${kind} "${name}" draws nothing`);
    plan[`${kind}s`].push({ name, first, last: drawn(slide), inside: open.section });
  }

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

    // The slide's one citation line, bottom left: author, journal, year. The one text the
    // lint allows under the size floor, and it finds the line by this name.
    citation(slide, text, box = {}) {
      slide.addText(text, {
        x: MARGIN, y: H - 0.5, w: W - 2 * MARGIN - 1.2, h: 0.3, ...box,
        fontFace: deck.font, fontSize: deck.size.citation, color: BLACK,
        margin: 0, valign: "bottom", objectName: "Citation",
      });
    },

    group(slide, name, draw) {
      named("group", slide, name, draw);
    },

    // One section of the slide: what `draw` draws shows and hides together, under `name`.
    section(slide, name, draw) {
      named("section", slide, name, draw);
    },

    // One click. `appear` and `disappear` each name a section or a group, or list several.
    click(slide, { appear, disappear, ...other } = {}) {
      if (Object.keys(other).length) {
        throw new Error(`deck.click: ${Object.keys(other).join(", ")} is not an effect; use appear and disappear`);
      }
      const click = { appear: listed(appear), disappear: listed(disappear) };
      if (!click.appear.length && !click.disappear.length) {
        throw new Error("deck.click names nothing to appear or disappear");
      }
      plan.clicks.push(click);
    },
  };
  return deck;
}

// Refuse a click that names nothing on the slide, or a thing a click already changed.
function checkClicks(plan) {
  const sections = new Set(plan.sections.map((one) => one.name));
  const groups = new Map(plan.groups.map((one) => [one.name, one.inside]));
  const used = new Set();
  plan.clicks.forEach((click, index) => {
    for (const name of [...click.appear, ...click.disappear]) {
      const where = `click ${index + 1} names "${name}"`;
      if (groups.has(name) && groups.get(name) !== null) {
        throw new Error(
          `${where}, a group inside section "${groups.get(name)}"; a click shows or hides the whole section`,
        );
      }
      if (!sections.has(name) && !groups.has(name)) {
        const known = [...sections, ...groups.keys()].map((one) => `"${one}"`).join(", ");
        throw new Error(`${where}, but the slide has no section or group of that name (it has: ${known || "none"})`);
      }
      if (used.has(name)) {
        throw new Error(
          `${where}, which a click already shows or hides; PowerPoint plays one effect per section`,
        );
      }
      used.add(name);
    }
  });
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

async function build({ id, source, output, plan: planned, notes, page }) {
  const pres = new PptxGenJS();
  pres.layout = "LAYOUT_WIDE";
  pres.title = job.title;
  pres.theme = { headFontFace: job.theme.font, bodyFontFace: job.theme.font };
  const plan = { objects: 0, groups: [], sections: [], clicks: [] };
  const deck = helpers(pres, plan);
  const slide = pres.addSlide();
  slide.background = { color: WHITE };
  // PptxGenJS writes a picture's whole path as its alt text when the source gives none, which
  // would put a path of this machine into a file people share. The file's name goes in instead.
  const addImage = slide.addImage.bind(slide);
  slide.addImage = (options = {}) => addImage({
    ...options,
    altText: options.altText || (options.path ? path.basename(options.path) : "Picture"),
  });
  try {
    const draw = require(source);
    if (typeof draw !== "function") {
      throw new Error("the file must export a function: module.exports = (slide, deck) => {}");
    }
    await draw(slide, deck);
    // PptxGenJS counts notes as a thing drawn, which would move every later shape id.
    if (slide._slideObjects.some((one) => one._type === "notes")) {
      throw new Error(`slide.addNotes is not used here; write the notes in notes/${id}.md`);
    }
    checkClicks(plan);
    if (page !== null) number(slide, deck, page);
    plan.objects = drawn(slide);
    // After everything drawn, so the notes take no shape's place in the drawing order.
    if (notes !== null) slide.addNotes(fs.readFileSync(notes, "utf8").trim());
    fs.writeFileSync(planned, JSON.stringify(plan));
    await pres.writeFile({ fileName: output });
  } catch (error) {
    console.error(`slide ${id} (slides/${id}.js): ${error.message}`);
    process.exit(1);
  }
}

(async () => {
  for (const slide of job.slides) await build(slide);
})();
