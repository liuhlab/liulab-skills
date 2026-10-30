# A lab skill for Feishu

The lab does not ship a `lab-feishu` skill. `/lab-setup` installs `lark-cli` and Feishu's
official `lark-*` skills, the lab defaults carry one rule for it, and the few facts the official
skills lack sit on one reference page under `lab-setup`.

## Why this is out of scope

Feishu's official skills already cover most of what a lab skill would say: which identity a
call runs as, the error format, missing scopes and the approval step for risky commands. They
ship with the CLI and update with it. A lab skill wrapping them would repeat that text and fall
behind each release.

What the official skills lack is short: how long a login lasts, and three Drive limits. That fits
on one page, `skills/lab-setup/references/feishu.md`.

## When to revisit

If lab work on Feishu grows a procedure of its own that the official skills cannot hold, such as
a repeatable sync between a repo and a Drive folder.

## Prior requests

- #137: "lab-feishu: a skill for the Feishu CLI (lark-cli)"
