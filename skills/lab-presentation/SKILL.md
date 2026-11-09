---
name: lab-presentation
description: >-
  Slides, a slide deck, a presentation, a talk, a pptx or PowerPoint file: use to build, edit
  or check a deck. The workflow is an audience brief, a text outline, the slides, a check of
  every click state, and speaker notes when wanted. Holds the numbered slide rules, the
  practice behind them and the `lab-deck` build.
---

# lab-presentation

Build a deck the audience can follow at speaking speed. `GLOSSARY.md` defines deck, deck
folder, audience brief, slide rule, deck lint and click state.

Every deck gets steps 1, 2 and 4, a three-slide update included. Rendered options and speaker
notes are extra, each with its own condition below. A recorded talk follows `hq-mode`'s `talk`
playbook after this workflow.

## Reference pages

Open a page in full at the step that needs it, not before.

| Page | Open it |
| --- | --- |
| [references/slide-rules.md](references/slide-rules.md) | Before the outline, and before any edit to a slide |
| [references/practice.md](references/practice.md) | When you plan the outline or the notes, or when the user questions a rule |
| [references/build.md](references/build.md) | At step 3, before you write a slide source or run `lab-deck` |
| [references/images.md](references/images.md) | When a slide needs a picture: a real figure panel, or one drawn with Codex |

## 1. The audience brief

The brief is `brief.toml` in the deck folder. Every later check reads it.

| Field | Holds | When missing |
| --- | --- | --- |
| `audience` | Who is listening | Ask |
| `knows` | What they already know | Ask |
| `minutes` | The length of the talk, as a number | Ask |
| `language` | The language of the slides, such as `"en"` or `"zh"` | Ask |
| `known_terms` | A list of the terms and abbreviations they need no help with | Ask |
| `room` | `"meeting room"` or `"hall"` | `"meeting room"` |
| `use` | `"presented"` or `"read alone"` | `"presented"` |

Read the brief when the deck folder has one. Fill every line the request and the source text
already answer. Then ask only for the lines still missing, in one message, and say how many
there are. Never ask for the room or the use: take the default and say so. Write no outline
while one of the first five lines is empty.

## 2. The text outline

Write the outline as text, before any slide exists. For each slide give the title, as the
sentence that states its conclusion, the body's phrases, and the figure it shows. Start from
about one slide per minute and one idea per slide. Settle the content with the user here.
Layout comes later.

## 3. The slides

Build the deck with `lab-deck`, in a deck folder, as the build page says. Commit in the deck
folder before you touch the deck and after each build, so the user's hand edits are in history
first.

For an edit to a deck that exists, slide rules 14 and 15 come first: say the slide and the
exact change in one line, then change only that.

Show 2 to 4 rendered options for a slide only when the user asks, or after the user rejects
the slide. Otherwise build one.

## 4. The check

- The deck lint stops the build on a blocking failure. Fix the slide. Never loosen a check.
- Fix every lint warning, or explain it in the reply. None passes in silence.
- Render every click state to a picture. After a build, look at each picture that changed.
  Before you report the deck finished, look at the whole deck once.
- Ask the user for one last look in PowerPoint itself. A Repair dialog shows only there.

## 5. Speaker notes

Write notes only when the user asks, or for a formal talk. Write them last, against the final
slides. Each note is an outline of the spoken point, in other words than the slide's. A line
the notes never say is a candidate to cut from the slide: propose the cut, and leave the slide
alone.

## Chinese decks

The same workflow, rules and size floor apply. `unslop-zh` covers the wording on the slides
and in the notes.

## Reply

The deck path, the slides changed, the pictures you looked at, each lint warning as fixed or
explained, and the open choices.
