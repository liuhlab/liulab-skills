# Test cost

A lab addition to the Standards axis, for a diff that adds, changes or deletes tests, or
touches a test limit. Every test spends from the suite's **budget**: the repo's `timeout` and
`suite_budget` in `pyproject.toml`, or else the test limits in the lab defaults
(`skills/lab-setup/references/defaults.md`, Tooling). The implementer is the one spending the
budget and rarely notices; the review is where the spend is counted.

Measure on one machine: time the test run on the merge-base and on `HEAD`, or read the pytest
step of both CI runs. Then report each item below.

1. **A loosened limit** is a hard violation unless the spec asked for it: a raised `timeout`
   or `suite_budget`, a `PYTEST_TIMEOUT` or `--timeout` anywhere, a new `skip`, `xfail` or
   deselect, or a `slow` mark with no reason given in the PR. Quote the hunk. A limit that
   went red is answered by a faster or a moved test, and its number changes only in a pull
   request of its own.
2. **The run's time:** both numbers and the growth, with the slowest new tests from
   `--durations=10`. A run over the budget is a hard violation; any growth is a finding.
3. **Count against the spec:** new tests set against the ticket's Tests line, or against the
   spec's acceptance criteria. A test past that count is Over-testing, a judgement call:
   name it and the test it repeats.
4. **Setup cost:** a fixture that rebuilds a costly state for each test, such as a database,
   a store or a worker pool, where tests could share one. → widen the fixture's scope, or
   check several fields of one result in one test.
