---
search:
  exclude: true
---

# The deck build ships with the plugin, not in each deck

The code that turns a deck folder into a PowerPoint file is one package, `src/lab_deck/`,
beside the Edison one. It runs from the repo's pixi environment as `lab-deck`, through a
`bin/` wrapper and the PATH link `/lab-setup` makes, exactly as `edison-cli` does (ADR 0014).
A deck folder holds content only: the brief, the slide order, one source file per slide,
pictures, notes, the theme and the built deck. It records no build version.

## Why

Each deck used to carry its own copy of the build, about 1,400 lines taken from the deck
before it. A fix made in one deck reached no other, no test covered any copy, and a slide
rule learned on one talk was missing from the next.

One package gives one place to fix and one set of tests in the gate.

## What it costs

- **A deck can stop building after an update.** A deck folder is written against the helpers
  of the day. When a later release changes them, an old deck fails until its slide sources are
  moved to the current build. The agent does that migration; no old build code is kept, and
  the deck names no version to fall back to.
- **A deck does not build without the plugin.** A deck folder sent to someone outside the lab
  is content and a built file, not a build.
- **The environment grows** for every member, including those who never make a deck.

## PptxGenJS comes from conda-forge

`pptxgenjs` 4.0.1 is a pixi dependency, pinned by `pixi.lock`, so no `npm install` runs on any
machine and there is no second lock file. The conda package lands in `lib/node_modules` under
the environment's prefix, and Node does not search that folder by itself.

Run in the environment, Node 22: `node -e 'require("pptxgenjs")'` fails with
`Cannot find module`. The same command with `NODE_PATH` set to `$CONDA_PREFIX/lib/node_modules`
loads it. So `lab_deck/build.py` sets `NODE_PATH` to that folder, for the one Node process it
starts. A slide source requires nothing itself: its helpers arrive as an argument.

## Rejected

**A build version recorded in the deck, with old builds kept.** A deck would always rebuild as
it was. It also keeps every old build alive, each with the defects its successor fixed, and
the lint and slide rules would differ deck by deck.

**`npm ci` into a cache outside the plugin, or the library's archive in the repo.** Each needs
an install step or a checksum of its own to maintain, where pixi already has both.
