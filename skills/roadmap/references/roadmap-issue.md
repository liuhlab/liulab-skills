# The roadmap issue

Title it `<goal>: stages` and label it `enhancement`. Two worked examples:
[Bulk GEO and SRA metadata store: stages](https://github.com/liuhlab/liulab-data/issues/18), drafted
straight from its Discussion, and
[Study understanding, the first 1%: stages](https://github.com/liuhlab/seqforge/issues/534),
drafted at the end of a map of maps.

## Body

```markdown
<The goal in two or three sentences. Background: <the Discussion>. This issue fixes the goal
and the stages only. Every design choice stays open until that stage's map.>

## Scope

<Only for a goal over a large set: a table of which rung (1%, 10%, 100%) this roadmap does,
per kind of work.>

## Final deliverable

<What exists when the goal is met, in one paragraph.>

Done when all <N> hold:

1. **<Name>.** <A check someone can run or read.>

## Stages

Each stage gets its own map when it starts. Each stage map is a sub-issue of this issue and
sits in the milestone <M>. Numbers follow the order the stages start.

| # | Stage | After | Outcome | Ends when |
|---|---|---|---|---|
| 1 | **<name>** | — | <what exists once it ends> | <a test, often "Check K passes"> |

## Known going in

- <A fact a stage builds on, marked measured or estimated, with its source.>

## Open, for the stage maps

- **<Stage>.** <The questions that stage's map settles.>

## Out of scope for this goal

- <Work ruled out, and when it could come back.>

## Decided

- <A principle every stage keeps.>
```

## Writing it

- **A done-when check can fail.** Someone tells pass from fail by reading a count, running a
  command or answering a query. A check that only reports numbers says "no targets".
- **An ends-when test names a check** when one fits. A check may land in whichever stage first
  makes it possible; say so under the stage table.
- **After** names the stages this one waits on, or "with N" for two that start together.
- **Decided holds principles only.** A design choice belongs to the stage that meets it, under
  Open, for the stage maps.
- **Known going in** carries each number with its evidence mark, so a stage map can trust it.
- **Scope and Out of scope fix the destination.** Work past it returns only as a new roadmap.

## Tracker commands

Run inside a clone; `gh` infers the repo. Sub-issues and blocking use the tracker doc's
Wayfinding operations, as wayfinder does.

- **List milestones**, to number the new one after them:
  `gh api --paginate 'repos/<owner>/<repo>/milestones?state=all' --jq '.[].title'`
- **Create the milestone**: `gh api --method POST repos/<owner>/<repo>/milestones -f title="M<n>: <goal>" -f description="<one sentence>"`
- **Put an issue or pull request in it**: `gh issue edit <n> --milestone "M<n>: <goal>"`, or
  `gh pr edit <n> --milestone "M<n>: <goal>"`.
- **Make a stage map a sub-issue of the roadmap**: `gh issue edit <roadmap> --add-sub-issue <map>`.
- **Stage order**: when a stage map waits on another, add a native blocked-by edge between the
  two maps, so the tracker shows which stage can start.
- **Close the milestone**: `gh api --method PATCH repos/<owner>/<repo>/milestones/<number> -f state=closed`
