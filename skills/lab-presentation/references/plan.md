# The slide plan

Open this page at step 3, once the user has approved the outline's flow and before any slide
is built.

The slide plan is one HTML page. It shows every slide of the deck as a mock-up beside a side
panel, so the user judges the slide and the talk together. It settles which slides exist, and
each slide's title and picture. The build then cuts the words and draws the pictures.

## Write the page

1. Copy the template, [../assets/plan.html](../assets/plan.html), to `plan.html` in the deck
   folder. It is one file with its styles inside, so it opens offline and on a phone.
2. Change the content only: the page title, the header line, and one `section` per slide in
   the order shown. Leave the styles alone.
3. Give each slide its id in `data-slide`: the name its source file will have at step 4. An id
   is a name, never a number, so a slide that moves keeps its id.
4. Run `lab-deck plan-lint`, and fix what it reports.
5. Commit the page in the deck folder.

## What goes where

| Part | Class | Holds |
| --- | --- | --- |
| The mock-up | `on-slide` | Only what will be on the slide, at about the real word count |
| Its title | `slide-title` | The slide's conclusion, as slide rule 2 asks |
| Its picture box | `slide-figure` | A label of a few words where the picture goes. Leave the box out of a slide with no picture |
| The planned picture | `planned-picture` | In the side panel. What the picture is and where it comes from, or `text only` |
| The rest of the side panel | none | What the presenter says, and the evidence: the source of each number and any caveat |

The two parts follow different rules. The mock-up obeys the slide rules: phrases, not
sentences, and no takeaway line the slide will not carry. The side panel may be wordy. A line
the audience will not see goes in the side panel, never in the mock-up.

Before you plan a picture, look for one to reuse, as "Reuse first" in [images.md](images.md)
says.

## The plan lint

`lab-deck plan-lint [<folder>]` reads `plan.html` in plain code, with no model and no build.
It prints its findings and exits 1 on a blocking failure. A warning leaves the exit at 0: fix
it, or explain it in the reply.

| Check | Severity | Fails when |
| --- | --- | --- |
| `plan-id` | Blocking | A slide has no `data-slide`, the id is not a slide name, or two slides share one |
| `plan-title` | Blocking | A mock-up has no `slide-title` text |
| `plan-picture` | Blocking | A slide has no `planned-picture` text: neither a picture nor `text only` |
| `plan-words` | Warning | A mock-up carries more words than the deck lint's `slide-words` limit, beside its title and its picture label |

- The word check counts the mock-up only, never the side panel.
- It uses the deck lint's own counter and limit, in [checks.md](checks.md#the-lint). The plan
  cannot promise more text than the slide may carry.
- A deck read alone, `use = "read alone"` in the brief, gets no `plan-words`.
- The mock-up's text is sized as a share of its width, so its proportions are near a slide's.
  It is still not the slide: the deck lint keeps the size floor.

## Show it and stop

Give the user the page. When the session has a tool that publishes a private page, publish
`plan.html` and give the link; otherwise give the file's full path. Never make the page
public.

Then stop, and ask one question: does the user approve which slides exist, and each slide's
title and picture? Apply what the user changes, run the lint, commit, and ask again. The
commit the user approves is the approved plan.

## After approval

Build the deck without a second question. Each planned slide becomes `slides/<id>.js` under
the same id.

| A change after approval | Needs the plan approved again |
| --- | --- |
| A slide added, dropped, moved or replaced | Yes |
| A title's conclusion changed | Yes |
| A picture changed, or `text only` changed to a picture | Yes |
| Words cut within an agreed point | No |
| A fix the deck lint or the picture check asks for | No |

For a change that needs approval, edit `plan.html` first, show it, and build after the yes.
