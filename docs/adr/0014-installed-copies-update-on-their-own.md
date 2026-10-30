---
search:
  exclude: true
---

# Installed copies update on their own, in every agent

Claude Code and Codex install the `lab` plugin from the `.claude-plugin/` files. Kimi Code
reads Claude Code's marketplace clone through `extra_skill_dirs`. All three update with no
one running a command: Claude Code through `autoUpdate: true` on the `liulab` entry under
`extraKnownMarketplaces`, Codex by upgrading its git marketplaces at startup, and Kimi by
reading the clone live. One user-invoked skill, `/lab-setup`, sets a machine up, and links
`bin/edison-cli` into a directory on the user's PATH for all three. Releasing is pushing. To
update Claude Code by hand, run `claude plugin marketplace update liulab`, then
`claude plugin update lab@liulab`. Codex uses its own plugin CLI. Development evals install
and verify a private snapshot through the selected agent; they never refresh another agent.

## Why automatic

ADR 0004 kept updates manual because background update "needs a `GITHUB_TOKEN` on every
machine". For a public repo it does not; the token was only ever for private marketplaces.
And under ADR 0008 every merge is a release, so a manual step leaves machines silently on old
copies, including old safety rules, which 0004 named as its own cost.

## Why Kimi reads the clone

Kimi's own plugin format updates only by reinstalling. Feeding `~/.agents/skills` makes Codex
load every skill twice and lets Kimi's user tier shadow the lab copies. `npx skills` ships no
`bin/` or `src/` and updates by hand. The clone is a git checkout on `main` that Claude Code
already keeps current.

## What it costs

- Kimi updates only on a machine that runs Claude Code, and lags its update pass. If Claude
  Code moves its clone, Kimi loads nothing; `/lab-setup` checks that the path exists.
- A bad release reaches every machine at its next launch, with no one choosing to pull it.
- A session without `/lab-setup` gets none of this.

## What this reverses

ADR 0004's "marketplace updates stay manual", and its token premise. Its CalVer half stands.

ADR 0011 rejected running `edison-cli` from the marketplace clone, because the Python that ran
would not be the Python that was installed. The PATH link does exactly that, and Claude Code
takes it ahead of the plugin's `bin/`. Accepted: in Claude Code and Codex, the skill text and
the Python it runs can come from different releases until both agents relaunch.

ADRs 0001 and 0008 stand.
