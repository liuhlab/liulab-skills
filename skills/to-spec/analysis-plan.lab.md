# Analysis-plan template

A lab addition to `to-spec`. When the work is an analysis, a question answered from data,
write the spec with this template in place of the one in `SKILL.md`. An analysis has no
actors, so a list of user stories would be invented. A tool, including one an analysis
needs built, keeps the template in `SKILL.md`.

Everything else in `SKILL.md` still applies: the seams, the glossary, publishing to the
tracker with its triage label.

```markdown
## Question

The question the analysis answers, and the decision or claim that waits on the answer.

## Data and provenance

Each input: where it comes from, which version, release or accession, how it was produced,
and anything already known to be wrong with it.

## Methods

The steps from raw data to result, with the tool and the parameters each step uses. For a
choice still open, the criterion that will settle it, fixed before any result is seen.

## Outputs

The figures and tables the analysis produces, and what each one shows.

## Validation and controls

How a result is checked: positive and negative controls, a known truth or held-out
benchmark, checks on counts and ranges, and the fixture the work reruns on. Each check
states its expected cost, and a check over a whole store is marked as needing the user's
yes before it runs.

## Out of scope

The questions, samples and data this analysis leaves out.
```
