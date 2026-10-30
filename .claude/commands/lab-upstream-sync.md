---
description: >-
  Maintainer only, run by hand in this repo about monthly. Merge upstream changes into every
  tracked skill from its pin, walk through what the merge reports and what is new in both
  upstreams, and open one pull request carrying one version bump and changelog entry, tagged on
  main once it merges.
disable-model-invocation: true
---

# Upstream sync

The monthly sync of `docs/adr/0012-upstream-skills-merge-from-a-pin.md`. The pins and the
attribution record are in `upstream/`, in the formats `upstream/README.md` gives. The merge is
`scripts/upstream_sync.py`, the same on every run; `--help` says what it does. You read its
report with the maintainer and decide nothing alone.

## Rules

- Never commit a conflict marker, and never resolve a conflict by dropping a lab edit or
  upstream text without the maintainer's yes.
- Upstream text changes only by a lab edit, which adds and never removes
  (`upstream/README.md`, "Lab edits"). Never edit it to pass the gate.
- Never run an eval case without the maintainer's yes for that case: each costs tokens.
- Show the pull request's title and body and wait for a yes before you push anything.

## Steps

1. From an up-to-date `main` with a clean tree, `git switch -c sync/upstream-<YYYY-MM>`.
2. For each `upstream/<name>/pin.json`, clone its `repo` fresh into a temporary directory:
   `git clone <repo> "$TMPDIR/sync-<name>"`.
3. Run the merge, with one `--clone` per pin:

   ```bash
   pixi run python scripts/upstream_sync.py merge \
     --clone mattpocock="$TMPDIR/sync-mattpocock" --clone pstack="$TMPDIR/sync-pstack"
   ```

   Exit 0: nothing to resolve. Exit 1: conflicts are left in the files. Exit 2: refused, with
   nothing written; stderr says why.
4. Go through the report with the maintainer, one section at a time.
   - **Conflicts.** For each file, show the lab, pinned and upstream texts between the markers,
     propose a resolution that keeps the lab edit on top of upstream's new text, and write it
     on a yes. For a file upstream deleted or renamed, find where its text went with
     `git -C <clone> log --stat -M <old pin>..HEAD` and port the edit there.
   - **Dropped edits.** A lab line the merge lost. Put it back on top of upstream's text.
   - **Stale words.** Lab text still using a name upstream retired. Find the new name in
     upstream's diff and propose the change to the lab text.
   - **Pin lost.** Every difference is a conflict. Keep the lab's edits and take upstream's text.
   - **Deleted upstream.** The skill is gone from the lab too. If it was renamed, port the lab
     edits the report lists into the new skill. To keep the old one instead, fork it (step 5).
   - **New skills.** Ask whether each one ships. To skip one, delete its directory, its pin
     entry and its line in both gate lists; it will not come back.
   - **Forked, not merged** and **Mapped items.** For each change, read
     `git -C <clone> diff <old pin>..HEAD -- <path>`, say in a sentence what upstream changed,
     and ask whether to port it by hand. A low-priority mark comes from commit subjects alone,
     so check it against the diff. A new pstack skill is an idea to take or leave.
5. To fork a tracked skill whose merge costs more than it saves, discard the run:

   ```bash
   git restore --staged --worktree -- skills upstream .vale.ini .markdownlint-cli2.yaml
   git clean -fdq -- skills
   pixi run python scripts/upstream_sync.py fork <name> --changes "<what the lab changes>"
   ```

   Commit the fork with the maintainer's reason, then rerun step 3.
6. Resolving a conflict is where a lab line goes missing, so before committing run
   `pixi run python scripts/upstream_sync.py recheck` with the same `--clone` flags, and settle
   what it lists as in step 4. Run `pixi run check` until it is green, and
   `git grep -n '^<<<<<<< lab'` until it finds nothing.
7. Bump `version` in `.claude-plugin/plugin.json` and add a `CHANGELOG.md` entry in the same
   commit, naming new and removed skills, ported lab edits and the commits both pins moved to.
   Tag it only in step 9.
8. Show the title and body, the report plus anything decided in step 4. On a yes, push the
   branch, then `gh pr create`. One sync is one pull request and one version.
9. Once it merges, on an up-to-date `main` and the maintainer's yes, tag the merged commit
   `v<version>` and `git push origin main --tags`, as `AGENTS.md` says.
10. If the report lists **Eval cases to rerun**, upstream touched a skill whose lab edit has a
    case. Use the development agent's verified installation. Ask about each case unless
    already authorized, then run `bash tests/eval.sh --agent <agent> --only <case>`.
    The runner installs and verifies an isolated snapshot. On a failure, read the
    transcript it names before calling the edit lost, then file an issue.
11. Delete the temporary clones.
