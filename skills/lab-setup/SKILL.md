---
name: lab-setup
description: >-
  Set up this machine for the lab plugin, once, after installing it: Claude Code auto-update,
  the plugin in Codex, Kimi Code reading the marketplace clone, edison-cli on PATH, and lark-cli
  logged in to Feishu. Use when the user types /lab-setup, asks to set up Codex or Kimi Code for
  the lab skills, wants the plugin to update by itself, asks to install or log in lark-cli, or
  asks which old skill copies shadow the plugin's. Also points each agent at the lab defaults.
  Confirms each change with the user and removes nothing. User-invoked only.
disable-model-invocation: true
---

# Set this machine up for the lab plugin

One script does the work: `scripts/lab_setup.py` in this skill's folder. It acts on the home
directory named on its command line, changes only what is not yet set up, and removes
nothing. A second run on a set-up machine changes no file, so a rerun repairs a half-done one.
Feishu's `lark-cli` is the exception: section 4 sets it up by hand.

| Step | What it sets up |
| --- | --- |
| `claude` | `autoUpdate: true` on the `liulab` entry under `extraKnownMarketplaces` in `~/.claude/settings.json` |
| `codex` | `codex plugin marketplace add liuhlab/liulab-skills`, then `codex plugin add lab@liulab` |
| `kimi` | the marketplace clone's `skills/` in `extra_skill_dirs` in `~/.kimi-code/config.toml` |
| `defaults` | one marked block pointing at [references/defaults.md](references/defaults.md) in `~/.claude/CLAUDE.md`, `~/.codex/AGENTS.md` and `~/.kimi-code/AGENTS.md`; a rerun replaces only the block |
| `edison-cli` | a link to the clone's `bin/edison-cli` in `~/.local/bin` or `~/bin`, whichever is on PATH |
| `clashes` | reports user-level skills that take a name the plugin ships; changes nothing |

## 1. Pick an interpreter

The script needs Python 3.11 or newer and nothing else. Use `python3` if
`python3 --version` says 3.11 or later; otherwise `pixi exec --spec "python>=3.11" python`.
With neither, stop: the user installs pixi from <https://pixi.sh> and runs `/lab-setup` again.

## 2. Show the plan

Run `<python> <skill dir>/scripts/lab_setup.py --home "$HOME" --dry-run`. If `CODEX_HOME` or
`KIMI_CODE_HOME` is set, pass its value as `--codex-home` or `--kimi-home`. Relay every line:

- **`refused`**: no marketplace clone. Stop and relay the install commands it prints. If the
  plugin *is* installed, Claude Code has moved its clone; say this skill needs a fix, and stop.
- **`would change`**: one change the script will make once the user says yes.
- **`skipped`**, the odd machine:
  - *No Codex or no Kimi Code*: nothing to set up for that agent. Say so and move on.
  - *No user bin folder on PATH*: offer to create `~/.local/bin` and add it to PATH in the
    user's shell profile. With a yes, do both, and run the step with
    `PATH="$HOME/.local/bin:$PATH"` in front of the command.
  - *`edison-cli` is already something else*: show it with `ls -l`. It stays unless the user
    removes it.
- **`clash`**: a user-level copy that shadows the plugin's skill of that name, in every
  agent, without a word. Name each path. What happens to it is the user's call; never delete
  it.
- **`failed`**: relay the reason. A file the script cannot read is the user's to fix.

## 3. Make the agreed changes

Ask about each `would change` line on its own. Then run once, naming only the steps the
user agreed to, for example
`<python> <skill dir>/scripts/lab_setup.py --home "$HOME" --only claude --only kimi`, and
relay what it prints. Each line should now read `changed` or `ok`.

## 4. Feishu's `lark-cli`, by hand

The script does not run these: the app and the login need the user in a browser or a terminal.
Offer them after the script and ask before each. Skip what is done: `command -v lark-cli` for
1, the `lark-*` folders in `~/.agents/skills` for 2, `lark-cli auth status --json` for 3 to 5,
`lark-cli config strict-mode` for 6.

1. `npm install -g @larksuite/cli`. No `npm`: the user installs Node.js.
2. `npx -y skills add https://open.feishu.cn -g --skill '*' -y`: Feishu's official `lark-*`
   skills, user-level.
3. An app: ask whether new or existing.
   - New: `lark-cli config init --new`. It blocks until the user finishes in the browser, so
     run it in the background and relay the link it prints.
   - Existing: the user runs, in their own terminal, with their App ID in place of `<id>`:
     `read -rs s; printf '%s' "$s" | lark-cli config init --app-id <id> --app-secret-stdin; unset s`.
     The secret goes only to the CLI's store: never ask for it, print it or write it down.
     Not a plain `config init`: see [references/feishu.md](references/feishu.md).
4. `lark-cli auth login --recommend`. It blocks too; relay its link at once, as it expires in
   minutes.
5. `lark-cli auth status --verify --json` must show `identities.user.status` as `ready`.
6. `lark-cli config strict-mode user --global`, the lab default; the user's yes to it is the
   confirmation the CLI's help asks for. Why: [references/feishu.md](references/feishu.md).

## 5. What happens next

- **Claude Code** checks the marketplace in the background after the first message of a
  session, and loads an update at the next launch. By hand:
  `claude plugin marketplace update liulab`, then `claude plugin update lab@liulab`.
- **Codex** upgrades the marketplace at every startup; restart it once now.
- **Kimi Code** reads the clone live, so it follows each Claude Code update.
- **`edison-cli`** works as a bare command in a new shell. `/lab-edison` checks the key.
- **`lark-cli`** keeps its login only while it is used: see
  [references/feishu.md](references/feishu.md).
- **The lab defaults** load in each new session. An edit to the page reaches every agent with
  the next update, no rerun. If the user once appended the old `CLAUDE-stub.md` rules to
  `~/.claude/CLAUDE.md`, say the page carries them now; removing that copy is the user's call.

## Rules

- Never remove a file, a link or an entry. A clash is reported, not fixed. Text outside the
  defaults block's markers is the user's.
- Run only the steps the user agreed to, and never against another `--home`.
