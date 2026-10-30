# lab-setup: one step after installing

Type it once on each machine, in Claude Code, right after the two install commands on the
[home page](../index.md#install):

```text
/lab-setup
```

From then on Claude Code, Codex and Kimi Code all use the lab skills, and all three keep them
up to date without you running anything. `edison-cli` works in all three as well.

## What it sets up

- **Claude Code** updates the plugin by itself. It checks in the background while you work,
  and a new release loads the next time you start it.
- **Codex** gets the same plugin, and checks for a new release each time it starts.
- **Kimi Code** reads the skills from the copy Claude Code keeps up to date, so it follows
  every Claude Code update.
- **`edison-cli`** gets a link in `~/.local/bin` or `~/bin`, whichever your shell already
  searches, so the command works outside Claude Code too.
- **`lark-cli`**, Feishu's command-line tool, if you want it. The agent installs it and
  Feishu's own skills, then hands you two steps in the browser: setting up an app and
  logging in. If you reuse an app, you type its secret into your own terminal, so the agent
  never sees it. The login lapses after 7 days without use; log in again when it does.
- **The lab's defaults** reach all three agents. Each agent's own notes file gets a short
  block that points at one page in the plugin. That page says where a repo's issues go,
  which labels to use, and the safety rules for the clusters. So a new repo needs no setup,
  and a change to the page reaches every agent with the next update.

If you don't have Codex or Kimi Code, it skips that part and says so.

It runs a small Python script, which needs Python 3.11 or newer. A fresh Mac has an older
one. There the agent runs it through [pixi](https://pixi.sh) instead, which lab-edison needs
anyway.

## It asks first, and removes nothing

The agent shows you every change before it makes one, and asks about each. You can say no to
any of them. Nothing on your machine is deleted, and a setting you wrote yourself stays as it
was.

Running it again is safe. On a machine that is already set up it changes nothing, and on a
machine that is half set up it finishes the job.

## Your own notes files

The block goes at the end of `~/.claude/CLAUDE.md`, `~/.codex/AGENTS.md` and
`~/.kimi-code/AGENTS.md`, between two marker lines. Text outside the markers is yours and
stays as you wrote it. A second run replaces only what sits between them.

If you once pasted the lab's safety rules into `~/.claude/CLAUDE.md` by hand, you can
delete that section now. The defaults page carries the same rules, and Codex and Kimi Code
get them too.

## Old copies of the same skills

You call a skill by its plain name, so an old copy in your own skills folder can win over
the plugin's copy without a word. `/lab-setup` lists every such copy and where it lives. It
leaves them alone: what to do with each one is your call. If you once installed skills with
`npx skills`, those are the copies to remove.

## Updating by hand

You don't need to. If you want a release before your agent picks it up:

```bash
claude plugin marketplace update liulab
claude plugin update lab@liulab
```

Then restart Claude Code.
