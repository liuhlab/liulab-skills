---
search:
  exclude: true
---

# `roadmap` is the third lab-owned naming exception

The lab-written skill for a goal bigger than one wayfinder map is named `roadmap`, typed bare.
The maintainer chose the bare name so it reads beside `wayfinder`, the adopted skill it charts
every map with: wayfinder draws a map, a roadmap is a map of maps. It does not become an adopted
skill and gets no upstream record. `hq-mode` and `unslop-zh` remain the other two exceptions to
the `lab-*` name for skills the lab wrote or derived.

`milestone` was the other candidate and lost. GitHub's Milestone is part of the workflow the skill
runs, since the roadmap and its stage maps sit in one, so one word would name both. In plain
English a milestone is also one point on the way, closer to a stage than to the goal.

## What it costs

A project or user skill named `roadmap` shadows the lab copy without a warning. `/lab-setup`
reports such copies and removes none. Lint names the three exceptions explicitly and still
requires `roadmap` to record its triggers. No other unrecorded bare name passes.

## What this changes

ADR 0016's statement that `hq-mode` and `unslop-zh` are the two exceptions. Its other decisions
stand, as do ADR 0013's rules for adopted skills.
