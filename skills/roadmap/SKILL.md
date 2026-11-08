---
name: roadmap
description: >-
  Plan a goal bigger than one wayfinder map as a roadmap: one issue with a final deliverable,
  done-when checks and stages, kept in a GitHub milestone. Each stage gets its own map, then
  spec, tickets and code. Charts the roadmap, starts and ends stages, and closes it when every
  check passes. User-invoked.
disable-model-invocation: true
---

# Roadmap

A **roadmap** is a map of maps. A goal arrives that one wayfinder map cannot hold: it needs
several specs, and its stages wait on each other. The roadmap fixes the goal and the **stages**
only. Every design choice stays open until that stage's own map. When every stage has landed, the
goal is met.

Three pieces, all on the repo's issue tracker:

- **Background**: a GitHub Discussion with the goal in the user's words and what exists today.
- **The roadmap issue**, titled `<goal>: stages`: the final deliverable with numbered
  **done-when checks**, and a stage table giving each stage an outcome and an **ends-when** test.
  Write it from [references/roadmap-issue.md](references/roadmap-issue.md), which also holds the
  tracker commands.
- **Stage maps**: one wayfinder map per stage, each a sub-issue of the roadmap. The roadmap, its
  stage maps, and each stage's spec, tickets and pull requests sit in one GitHub milestone,
  `M<n>: <goal>`. A map's decision tickets stay out of it.

Every map here is a wayfinder map: read [wayfinder](../wayfinder/SKILL.md) before charting one.
Its tickets, fog and resolution rules hold unchanged.

## Chart the roadmap

The user invokes with a goal.

1. **Write the goal down.** Find or post its Discussion. Done when the Discussion is linked.
2. **Chart the roadmap's map**: a wayfinder map whose destination is the roadmap issue. Its
   Notes say: each ticket settles only what placing a stage needs, and the rest goes to that
   stage's map; grilling tickets may be taken in waves, several per session. Its last ticket is
   "Draft the roadmap". Skip this map when the Discussion already makes the stages clear.
3. **Ask the scale question.** A goal over a large set climbs in rungs: 1% (early proof), 10%
   (scale proof), 100% (the full run). The roadmap does one rung, and its last check is that the
   next rung can be planned from measured cost, time and failure rate.
4. **Draft on a review page.** Publish the draft as an artifact: the stages as a diagram, the
   done-when checks, one section per stage, the calls you made and the questions left. Done when
   the user agrees with the page.
5. **File it.** Create the roadmap issue and its milestone, and put the roadmap in it. Place every
   item still open on the map under the stage that meets it. Close "Draft the roadmap" and the
   map, with the roadmap in its Decisions so far.

## Work the roadmap

The user invokes with the roadmap. Load its body and comments, not the stage maps' tickets.

- **Start a stage** when its After column allows. Chart its wayfinder map. Its
  destination is usually a build spec for this stage, with the stage's ends-when test as the spec's
  acceptance. Its Notes carry what earlier stages measured and the roadmap's open items for this
  stage. Make the map a sub-issue of the roadmap, add it to the milestone, and comment on the
  roadmap that the stage has started, naming its map.
- **End a stage** when its ends-when test holds. Comment on the roadmap with the evidence (what
  ran, against what, the numbers), the follow-ups, and every done-when check's status in a table.
- **Change the plan** by editing the roadmap body: a stage added, reordered or split, a check
  reworded. Say what changed and why in a comment.
- **Close the roadmap** when every done-when check has passed, each with its evidence comment.
  Close the milestone with it.
