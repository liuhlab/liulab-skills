# Feishu: what the official skills leave out

> **Provenance** — Source: `lark-cli` 1.0.98, its `--help`, a fresh login and the Feishu agent-integration docs · Checked: 2026-10-30 · Default tier: read.
> A claim at another tier is tagged `[verified]`, `[read]` or `[unverified]` where it is made.

Read this before a lab task that keeps a login alive or pushes files to Drive. The official
skills cover everything else: identity and `--as`, the error envelope on stderr, missing
scopes, the high-risk approval step (exit 10, `--yes`) and `auth status --verify`. Read them
with `lark-cli skills read lark-shared` and `lark-cli skills read lark-drive`, or from the
installed copies. Nothing from them is repeated here. Setup is step 5 of `SKILL.md`.

## Setup

To reuse an app, pass `--app-id` to `config init`, as `SKILL.md` does. A plain interactive
`config init` can keep an old App ID and pair it with the new secret, and every call then
fails with `invalid_client` (code 20002).

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
- `drive +version-history` lists a file's old versions `[verified]`. How long Drive keeps
  them is **open**.
- `drive +upload --file-token <token>` is documented to overwrite a file in place. Whether
  it does on the lab tenant is **open** `[unverified]`; check the file's version history
  after the first one.
