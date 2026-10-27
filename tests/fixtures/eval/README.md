# Eval assertion fixtures

Synthetic transcripts, used by the `eval assertions` section of `tests/lint.sh` to test the
rules in `tests/eval.sh` without an API call. `tests/eval.sh --dump` prints the real
assertions, so these test the rules that actually run rather than copies that would drift.
For stream-json fixtures, text assertions read the final `result`, while SKILL reads assistant
`tool_use` events.

| Suffix | Must |
| --- | --- |
| `.pass.txt` | match EXPECT, ALSO and EXTRA, clear DENY and satisfy SKILL |
| `.fail-expect.txt` | NOT match EXPECT |
| `.fail-deny.txt` | match DENY |
| `.fail-also.txt` | NOT match ALSO |
| `.fail-extra.txt` | NOT match EXTRA |
| `.fail-skill.txt` | violate SKILL by missing a required call or making a forbidden call |

A suffix may carry a label before `.txt`, as in `hq-pause-merge.fail-deny-close.txt`. Lint tests
each labelled fixture on its own, with its suffix's rule, so one case can hold two transcripts
that one rule must each catch. Lint fails a fixture whose suffix is none of these.

Nothing here is a real transcript and nothing here contains a real credential. Several are
regressions: a case that once reported a correct run as failed keeps its transcript here so
the assertion can never drift back.
