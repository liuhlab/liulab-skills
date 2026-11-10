# roadmap: a goal bigger than one map

Some goals are too big for one wayfinder map: several specs, months of work, and stages that wait
on each other. A roadmap is a map of maps. It is one issue that states the final deliverable,
the checks that say it is done, and the stages that get there. Each stage gets its own wayfinder
map when it starts, then its spec, tickets and code. When every stage has landed, the goal is met.

## You ask for it by name

```text
/roadmap every GEO sequencing study gets a study reading, on a pilot first
```

To work a roadmap that already exists, give its issue:

```text
/roadmap <roadmap issue URL>: start the bounding stage
```

## Charting a roadmap

1. The goal is written down as a GitHub Discussion.
2. A wayfinder map works out the principles the stages rest on. Its last ticket drafts the
   roadmap. When the stages are already clear, this map is skipped.
3. A goal over a large dataset climbs 1%, then 10%, then 100%. A roadmap does one of these steps,
   and ends ready to plan the next.
4. The draft goes up as a review page. You comment until you agree with it.
5. The roadmap is filed as an issue in a new GitHub milestone, and the planning map closes.

## Working a roadmap

- **Start a stage**: its own wayfinder map, usually ending in a build spec whose acceptance is the
  stage's end test. The map hangs under the roadmap and joins the milestone.
- **End a stage**: a comment on the roadmap with the evidence and where each final check stands.
- **Change the plan**: the roadmap is edited, with a comment saying why.
- **Close it** when every final check has passed.

## Examples

- [Bulk GEO and SRA metadata store: stages](https://github.com/liuhlab/liulab-data/issues/18)
- [Study understanding, the first 1%: stages](https://github.com/liuhlab/seqforge/issues/534)
