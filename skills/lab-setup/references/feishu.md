# Feishu: what the official skills leave out

> **Provenance** — Source: `lark-cli` 1.0.98, its `--help`, a fresh login and the Feishu agent-integration docs · Checked: 2026-10-30 · Default tier: read.
> A claim at another tier is tagged `[verified]`, `[read]` or `[unverified]` where it is made.

Read this before a lab task that keeps a login alive or pushes files to Drive. The official
skills cover everything else: identity and `--as`, the error envelope on stderr, missing
scopes and the high-risk approval step (exit 10, `--yes`). Read them with
`lark-cli skills read lark-shared` and `lark-cli skills read lark-drive`, or from the
installed copies. Setup is section 4 of `SKILL.md`.

## Setup

To reuse an app, pass `--app-id` to `config init`, as `SKILL.md` does. A plain interactive
`config init` can keep an old App ID and pair it with the new secret, and every call then
fails with `invalid_client` (code 20002).

## Identity

- With no user login, `lark-cli auth status` reports `"identity": "bot"` `[verified]`: a call
  without `--as` then runs as the bot, and any file it creates belongs to the bot's app.
- `lark-cli config strict-mode user` makes implicit calls run as the user and refuses
  `--as bot`. Its help forbids an agent from changing it without the user's yes. The lab
  default is `user`, set with `--global` so every profile inherits it; a profile's own
  setting overrides the global one.
- Strict mode alone does not hold: when the CLI cannot load the account, it treats strict
  mode as off (read in the source, `ResolveStrictMode`). Hence the lab rule of `--as user` on
  every call.

## Login life

- The access token lasts 2 hours after it is granted, and the refresh token 7 days
  `[verified]`, measured on a fresh login. Each refresh restarts the 7 days.
- A forced new login comes 365 days after the grant, however often it refreshes.
- The CLI refreshes only when a command runs. A machine that runs no `lark-cli` command for
  7 days is logged out; the user runs `lark-cli auth login --recommend` again.
- `lark-cli auth status` exits 0 when logged out, so a script or a service cannot test its
  exit code. Run `lark-cli auth status --verify --json`, once a day for a service, and read
  `identities.user.status`: `ready` is logged in `[verified]`.
- A failed login shows as `error.type` `authentication`, with a subtype. `token_missing`,
  `refresh_token_expired`, `refresh_token_revoked` and `refresh_token_reused` need a new
  login by the user. `refresh_server_error` means retry later.
- A lost reply to a refresh request can delete the stored login (larksuite/cli#2830, open as
  of the check date). Then the only fix is a new login.

## Drive

- A folder holds at most 1,500 items. Split a large upload across subfolders.
- Drive rejects an empty file. Skip or fill zero-byte files before an upload.
- `drive +push` has no exclude option `[verified]`: it uploads `.DS_Store`, lock files and
  anything else in the folder. Push a clean copy of the folder, not a working tree.
- `drive +upload --file-token <token>` overwrites a file in place on the lab tenant
  `[verified]`: same token, one file in the folder, new content, and a new `version` in the
  reply.
- The old version is kept `[verified]`: `drive +version-history` lists it, and
  `drive +version-get --version <version>` downloads it. No source says how long Drive
  keeps it, so don't count on an old version lasting.
