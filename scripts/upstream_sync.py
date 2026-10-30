#!/usr/bin/env python3
"""The upstream sync's merge-and-report step.

The maintainer runs it from `/lab-upstream-sync` (`.claude/commands/`), on a clean branch of
this repo, about monthly (`docs/adr/0012-upstream-skills-merge-from-a-pin.md`). It reads the
pins and the attribution record from `upstream/` (formats: `upstream/README.md`), reads each
upstream only through a fresh clone given on the command line, and writes only the lab tree.
It never touches the network.

`merge` takes a clone of every upstream with a pin. For a `merge` pin it brings every tracked
skill from the pin to upstream's tip, one file at a time, with `git merge-file`: the lab copy
is ours, the file at the pin is the base, the tip's is theirs. A skill is found under
`skills_dir` by its frontmatter `name`, so a bucket move costs nothing. A conflict is left in
the file between `<<<<<<< lab` and `>>>>>>> upstream`, with the pinned text between
`||||||| pinned` and `=======`. A skill gone from the tip is deleted or renamed: its lab copy,
pin entry and gate exemption go, unless the lab forked it. A skill upstream's plugin manifest
lists at the tip and not at the pin arrives under its own name. A forked skill is never
merged; the report says what upstream did to its original. If the pinned commit is gone from
the clone, because upstream rewrote its history, every difference between the lab copy and
the tip is marked as a conflict instead. For a `review` pin nothing is merged: the report has
a line per mapped item, a change whose every commit subject reads as a token cut or a model
change marked low priority, and a line per new skill. Every pin then moves to its tip, and
a Markdown report goes to stdout.

The report also carries two checks that a clean merge hides, and the eval cases to rerun.

- Stale words: a code span or file name under `skills_dir` at the pin and gone at the tip,
  still used in lab text. Lab text is every Markdown file git sees in the lab tree except
  `CHANGELOG.md` and `docs/adr/`, which are history; in a tracked skill, only the lines
  upstream wrote neither at the pin nor at the tip. A new lab page is covered the day it lands.
- Dropped edits: a line the lab added against the old pin that no file of its skill has now.
- Eval cases: each case in `tests/eval.sh` named `<skill>-*`, for a tracked skill whose
  upstream files changed. A case costs tokens, so the report only lists it.

`recheck` reruns both checks on the tree as it stands, against the lab at `--since` (default
`HEAD`, the sync not yet committed), so a lab line lost while resolving a conflict is caught.

`fork` makes a tracked skill lab-owned: its pin entry becomes an attribution record taken at
the pin's commit. Run it on a tree the merge has not touched, and commit it on its own.

Exit status: 0, done and nothing left to resolve; 1, done, with conflicts left in the files
(`merge`), or with something listed (`recheck`); 2, refused, with nothing written.
"""

from __future__ import annotations

import argparse
import difflib
import json
import posixpath
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

#: Where an upstream keeps its plugin manifest, relative to the directory holding `skills_dir`.
MANIFESTS = (".claude-plugin/plugin.json", ".cursor-plugin/plugin.json")
#: What the merge writes. It refuses to start while any of it has uncommitted changes, so that
#: everything it does can be read with `git diff` and undone with `git restore`.
WRITES = ("skills", "upstream", ".vale.ini", ".markdownlint-cli2.yaml")
ATTRIBUTION = "upstream/attribution.json"
#: The agent evals. A case named `<skill>-*` guards a lab edit to that skill (upstream/README.md).
EVALS = "tests/eval_cases.sh"
_CASES_RE = re.compile(r'^CASES="([^"]*)"', re.MULTILINE)
VALE = ".vale.ini"
MARKDOWNLINT = ".markdownlint-cli2.yaml"
#: The adopted-skill section of `.vale.ini` and the filter lines of the markdownlint override:
#: the same two patterns `tests/lint.sh` reads.
_VALE_RE = re.compile(r"^\[skills/\{([^}]*)\}/\*\.md\][ \t]*$", re.MULTILINE)
_MDL_RE = re.compile(r'^([ \t]*)-[ \t]*"skills/([^/"*{}]+)/\*\*"[ \t]*\n', re.MULTILINE)
_NAME_RE = re.compile(r"^name:\s*(.+?)\s*$")
#: A Markdown code span: what the stale-word check takes for a word upstream can remove.
_CODE_RE = re.compile(r"`([^`\n]+)`")
#: Lab text the stale-word check skips, because it records what was true when it was written.
HISTORY = ("CHANGELOG.md", "docs/adr/")
#: A reviewed item whose every commit subject matches this only cut tokens or moved a default
#: model. pstack tunes its text for frontier models in Cursor, and the lab runs other agents on
#: other models, so the summary marks such a change low priority (ADR 0012).
LOW_PRIORITY = re.compile(
    r"\b(tokens?|distill\w*|cuts?|trim\w*|shorten\w*|density|opus|sonnet|haiku|grok|fable"
    r"|gpt[\w.-]*|gemini|composer|model names?|default models?)\b",
    re.IGNORECASE,
)


class RefusalError(Exception):
    """A reason the sync will not run. Raised before anything is written."""


# ---------------------------------------------------------------------------------------------
# git


def _git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    run = subprocess.run(["git", *args], cwd=cwd, capture_output=True, check=False)
    if check and run.returncode != 0:
        detail = run.stderr.decode(errors="replace").strip()
        raise RefusalError(f"`git {' '.join(args)}` failed in {cwd}: {detail}")
    return run


def _ls_tree(root: Path, ref: str, prefix: str) -> dict[str, tuple[str, str]]:
    """Every file under `prefix` at `ref` in the repo at `root`, as path -> (mode, blob)."""
    out = _git(root, "ls-tree", "-r", "-z", ref, "--", prefix).stdout.decode()
    found: dict[str, tuple[str, str]] = {}
    for record in filter(None, out.split("\0")):
        meta, path = record.split("\t", 1)
        mode, kind, sha = meta.split()
        if kind == "blob":
            found[path] = (mode, sha)
    return found


@dataclass(frozen=True)
class Blob:
    """One file's content and its git mode, `100644` or `100755`."""

    mode: str
    data: bytes


#: A skill's files, keyed by path relative to the skill's directory.
Files = dict[str, Blob]


class Clone:
    """A fresh clone of one upstream, read at any commit it holds."""

    def __init__(self, root: Path) -> None:
        if _git(root, "rev-parse", "--verify", "--quiet", "HEAD", check=False).returncode != 0:
            raise RefusalError(f"{root} is not a git clone with a commit at HEAD")
        self.root = root
        self._blobs: dict[str, bytes] = {}

    def has(self, commit: str) -> bool:
        """Whether `commit` is a commit in this clone."""
        return (
            _git(self.root, "cat-file", "-e", f"{commit}^{{commit}}", check=False).returncode == 0
        )

    def tip(self) -> str:
        """Return the full commit at `HEAD`, which a fresh clone puts at upstream's tip."""
        return _git(self.root, "rev-parse", "HEAD").stdout.decode().strip()

    def entries(self, commit: str, prefix: str) -> dict[str, tuple[str, str]]:
        """Every file under `prefix` at `commit`, as path -> (mode, blob)."""
        return _ls_tree(self.root, commit, prefix)

    def blob(self, sha: str) -> bytes:
        """Return the content of one blob, read once: most files are the same at both ends."""
        if sha not in self._blobs:
            self._blobs[sha] = _git(self.root, "cat-file", "blob", sha).stdout
        return self._blobs[sha]

    def text(self, commit: str, path: str) -> str | None:
        """Return the file at `path` in `commit`, or None when there is none."""
        run = _git(self.root, "show", f"{commit}:{path}", check=False)
        return run.stdout.decode(errors="replace") if run.returncode == 0 else None

    def exists(self, commit: str, path: str) -> bool:
        """Whether `commit` has a file or directory at `path`."""
        return _git(self.root, "cat-file", "-e", f"{commit}:{path}", check=False).returncode == 0

    def diffstat(self, old: str, new: str, paths: list[str]) -> tuple[int, int] | None:
        """Return the lines added and removed under `paths`, or None when nothing changed."""
        out = _git(self.root, "diff", "--numstat", old, new, "--", *paths).stdout.decode()
        rows = [row.split("\t", 2) for row in out.splitlines() if row]
        if not rows:
            return None
        return (
            sum(int(a) for a, _, _ in rows if a != "-"),
            sum(int(r) for _, r, _ in rows if r != "-"),
        )

    def commits(self, old: str, new: str, paths: list[str]) -> list[tuple[str, str]]:
        """Return each commit after `old` up to `new` that touches `paths`: commit, subject."""
        out = _git(self.root, "log", "--format=%H%x09%s", f"{old}..{new}", "--", *paths)
        rows = [row.split("\t", 1) for row in out.stdout.decode().splitlines() if "\t" in row]
        return [(sha, subject) for sha, subject in rows]


def frontmatter_name(text: str) -> str | None:
    """Return the `name:` of a SKILL.md's frontmatter, or None when it has none."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for line in lines[1:]:
        if line.strip() == "---":
            return None
        match = _NAME_RE.match(line)
        if match:
            return match.group(1).strip("\"'")
    return None


class Snapshot:
    """An upstream's skills at one commit: found by frontmatter name, read file by file."""

    def __init__(self, clone: Clone, commit: str, skills_dir: str) -> None:
        self.clone = clone
        self.commit = commit
        self.entries = clone.entries(commit, skills_dir)
        self.listed_dirs = self._manifest(skills_dir)
        dirs: dict[str, list[str]] = {}
        #: Every directory holding a SKILL.md, named or not.
        self.dirs = {
            posixpath.dirname(path)
            for path in self.entries
            if posixpath.basename(path) == "SKILL.md"
        }
        for path, (_, sha) in sorted(self.entries.items()):
            if posixpath.basename(path) == "SKILL.md":
                name = frontmatter_name(clone.blob(sha).decode(errors="replace"))
                if name:
                    dirs.setdefault(name, []).append(posixpath.dirname(path))
        # Two directories wearing one name, as during a bucket move: the manifest's one wins.
        self.skills = {
            name: next((d for d in found if self._listed(d)), found[0])
            for name, found in dirs.items()
        }

    def _manifest(self, skills_dir: str) -> list[str] | None:
        """Return the skill directories the plugin manifest lists, or None with no manifest."""
        root = posixpath.dirname(skills_dir.rstrip("/"))
        for name in MANIFESTS:
            text = self.clone.text(self.commit, posixpath.join(root, name))
            if text is None:
                continue
            listed = json.loads(text).get("skills", [])
            listed = [listed] if isinstance(listed, str) else listed
            return [posixpath.normpath(posixpath.join(root, entry)) for entry in listed]
        return None

    def _listed(self, directory: str) -> bool:
        if self.listed_dirs is None:
            return True
        return any(directory == d or directory.startswith(d + "/") for d in self.listed_dirs)

    def listed(self) -> set[str]:
        """Return the names of the skills the plugin manifest ships."""
        return {name for name, d in self.skills.items() if self._listed(d)}

    def files(self, name: str) -> Files:
        """Return the files of skill `name`, keyed by path inside its directory."""
        prefix = self.skills[name] + "/"
        return {
            path.removeprefix(prefix): Blob(mode, self.clone.blob(sha))
            for path, (mode, sha) in self.entries.items()
            if path.startswith(prefix)
        }

    def tokens(self) -> set[str]:
        """Every code span in the Markdown under `skills_dir`, and every file's name there."""
        found: set[str] = set()
        for path, (_, sha) in self.entries.items():
            found.add(posixpath.basename(path))
            if path.endswith(".md"):
                text = self.clone.blob(sha).decode(errors="replace")
                found.update(m.group(1).strip() for m in _CODE_RE.finditer(text))
        return found


# ---------------------------------------------------------------------------------------------
# The lab tree


@dataclass
class Pin:
    """One `upstream/<upstream>/pin.json`, read and written in the format upstream/README.md gives."""

    upstream: str
    path: Path
    data: dict[str, Any]

    @property
    def commit(self) -> str:
        """The commit last synced or reviewed."""
        return self.data["commit"]

    @property
    def items(self) -> dict[str, str]:
        """Upstream item name to the lab path it feeds."""
        return self.data["items"]

    @property
    def repo(self) -> str:
        """The upstream's clone URL."""
        return self.data["repo"]

    @property
    def merges(self) -> bool:
        """Whether its items are tracked skills, merged on each sync, rather than only reviewed."""
        return self.data["sync"] == "merge"

    @property
    def skills_dir(self) -> str:
        """Where the upstream keeps its skills, with no trailing slash."""
        return self.data["skills_dir"].rstrip("/")

    def save(self) -> None:
        """Write the pin back, two-space indented as the README shows it."""
        text = json.dumps(self.data, indent=2, ensure_ascii=False) + "\n"
        self.path.write_text(text, encoding="utf-8")

    def move_to(self, commit: str) -> None:
        """Record `commit` as the one last synced or reviewed, and write the pin back."""
        self.data["commit"] = commit
        self.save()


class Lab:
    """The lab tree: this repo, or a fixture shaped like it."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def pins(self) -> dict[str, Pin]:
        """Every pin under `upstream/`, keyed by upstream short name."""
        pins: dict[str, Pin] = {}
        for path in sorted((self.root / "upstream").glob("*/pin.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except ValueError as e:
                raise RefusalError(f"{path} is not valid JSON: {e}") from e
            keys = ("repo", "commit", "sync", "skills_dir", "items")
            if not isinstance(data, dict) or any(k not in data for k in keys):
                raise RefusalError(f"{path} lacks one of {', '.join(keys)} (upstream/README.md)")
            pins[path.parent.name] = Pin(path.parent.name, path, data)
        if not pins:
            raise RefusalError(f"no upstream/<upstream>/pin.json under {self.root}")
        return pins

    def attribution(self) -> dict[str, Any]:
        """Return the attribution records, keyed by lab path; empty when the file is absent."""
        path = self.root / ATTRIBUTION
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}

    def save_attribution(self, records: dict[str, Any]) -> None:
        """Write the records in the README's shape, each source on one line."""
        (self.root / ATTRIBUTION).write_text(dump_attribution(records), encoding="utf-8")

    def require_clean(self) -> None:
        """Refuse a tree that is not a git checkout, or that has changes the sync would mix in."""
        run = _git(self.root, "status", "--porcelain", "--untracked-files=all", "--", *WRITES)
        if run.stdout.strip():
            raise RefusalError(
                "uncommitted changes under "
                + ", ".join(WRITES)
                + ": commit or discard them first, so `git diff` shows the sync and nothing else\n"
                + run.stdout.decode(errors="replace").rstrip()
            )

    def pin_at(self, ref: str, upstream: str) -> dict[str, Any] | None:
        """Return upstream's pin as committed at `ref`, or None when there was none."""
        run = _git(self.root, "show", f"{ref}:upstream/{upstream}/pin.json", check=False)
        return json.loads(run.stdout) if run.returncode == 0 else None

    def files_at(self, ref: str, path: str) -> Files:
        """Return the files under `path` as committed at `ref`, keyed by path inside it."""
        return {
            rel.removeprefix(path + "/"): Blob(
                mode, _git(self.root, "cat-file", "blob", sha).stdout
            )
            for rel, (mode, sha) in _ls_tree(self.root, ref, path).items()
            if mode != "120000"
        }

    def lines(self, path: str) -> set[str]:
        """Return every line of every text file under `path` as it is on disk."""
        root = self.root / path
        found: set[str] = set()
        for file in sorted(root.rglob("*")) if root.is_dir() else [root]:
            if file.is_file() and not file.is_symlink():
                found.update(_lines(file.read_bytes()))
        return found

    def text_paths(self) -> list[str]:
        """Return where the lab text is: every Markdown file git sees here, history and links out.

        Tracked or not yet added, wherever it lives, so a new lab page is covered the day it
        is written. A tracked skill's files are in the list too; the stale-word check reads only
        the lines of them that upstream did not write.
        """
        out = _git(
            self.root, "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", "*.md"
        ).stdout.decode()
        return [
            path
            for path in sorted(set(filter(None, out.split("\0"))))
            if not any(path == h or (h.endswith("/") and path.startswith(h)) for h in HISTORY)
            and (self.root / path).is_file()
            and not (self.root / path).is_symlink()
        ]

    def files(self, path: str) -> Files:
        """Return the tracked files of the lab skill at `path`, keyed by path inside it."""
        out = _git(self.root, "ls-files", "-s", "-z", "--", path).stdout.decode()
        found: Files = {}
        for record in filter(None, out.split("\0")):
            meta, rel = record.split("\t", 1)
            mode = meta.split()[0]
            found[rel.removeprefix(path + "/")] = Blob(mode, (self.root / rel).read_bytes())
        return found

    def write(self, rel: str, blob: Blob | None) -> None:
        """Write `blob` at `rel`, or delete the file there when it is None."""
        path = self.root / rel
        if blob is None:
            if path.exists():
                path.unlink()
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(blob.data)
        path.chmod(0o755 if blob.mode == "100755" else 0o644)

    def remove_skill(self, path: str) -> None:
        """Delete a skill's directory."""
        shutil.rmtree(self.root / path, ignore_errors=True)


def dump_attribution(records: dict[str, Any]) -> str:
    """Format the records as upstream/README.md shows them, each source on one line."""
    if not records:
        return "{}\n"
    out = ["{"]
    for i, (path, record) in enumerate(records.items()):
        out.append(f"  {json.dumps(path)}: {{")
        fields = list(record.items())
        for j, (key, value) in enumerate(fields):
            comma = "," if j < len(fields) - 1 else ""
            if key == "from" and isinstance(value, list):
                out.append('    "from": [')
                sources = [f"      {json.dumps(s, ensure_ascii=False)}" for s in value]
                out.append(",\n".join(sources))
                out.append(f"    ]{comma}")
            else:
                out.append(f"    {json.dumps(key)}: {json.dumps(value, ensure_ascii=False)}{comma}")
        out.append("  }" + ("," if i < len(records) - 1 else ""))
    out.append("}")
    return "\n".join(out) + "\n"


def update_gate_lists(lab: Lab, add: set[str], drop: set[str]) -> list[str]:
    """Add and drop names in the two gate lists that exempt upstream text.

    Returns a line for each list that could not be edited, for the maintainer to do by hand.
    """
    misses: list[str] = []
    if not add and not drop:
        return misses
    vale = lab.root / VALE
    text = vale.read_text(encoding="utf-8") if vale.exists() else ""
    match = _VALE_RE.search(text)
    if match:
        names = {n.strip() for n in match.group(1).split(",") if n.strip()}
        names = sorted((names | add) - drop)
        text = text[: match.start(1)] + ",".join(names) + text[match.end(1) :]
        vale.write_text(text, encoding="utf-8")
    else:
        misses.append(f"`{VALE}` has no `[skills/{{...}}/*.md]` section")
    mdl = lab.root / MARKDOWNLINT
    text = mdl.read_text(encoding="utf-8") if mdl.exists() else ""
    lines = list(_MDL_RE.finditer(text))
    if lines:
        names = sorted(({m.group(2) for m in lines} | add) - drop)
        indent = lines[0].group(1)
        block = "".join(f'{indent}- "skills/{n}/**"\n' for n in names)
        text = text[: lines[0].start()] + block + text[lines[-1].end() :]
        mdl.write_text(text, encoding="utf-8")
    else:
        misses.append(f'`{MARKDOWNLINT}` has no `- "skills/<name>/**"` filter lines')
    return misses


# ---------------------------------------------------------------------------------------------
# Merging


@dataclass
class FileMerge:
    """One file of one tracked skill: the three inputs, what was written and what is left."""

    path: str  # repo-relative lab path
    base: Blob | None
    ours: Blob | None
    theirs: Blob | None
    result: Blob | None
    conflicts: int = 0
    why: str = ""  # a conflict that is not a text hunk, in words


def _merge_file(ours: bytes, base: bytes, theirs: bytes) -> tuple[bytes, int] | None:
    """Run `git merge-file` on three texts: the merged text and its conflict count, or None.

    `--diff3` is explicit, so a maintainer's `merge.conflictStyle` cannot change the result.
    """
    with tempfile.TemporaryDirectory() as tmp:
        paths = []
        for name, data in (("lab", ours), ("pinned", base), ("upstream", theirs)):
            path = Path(tmp) / name
            path.write_bytes(data)
            paths.append(str(path))
        labels = ["-L", "lab", "-L", "pinned", "-L", "upstream"]
        run = subprocess.run(
            ["git", "merge-file", "-p", "--diff3", *labels, *paths],
            cwd=tmp,
            capture_output=True,
            check=False,
        )
    if run.returncode < 0 or run.returncode > 127:
        return None
    return run.stdout, run.returncode


def three_way(path: str, base: Files, ours: Files, theirs: Files) -> list[FileMerge]:
    """Merge every file of one skill, keyed by path inside it, with `base` as the pin."""
    merges = []
    for rel in sorted(set(base) | set(ours) | set(theirs)):
        b, o, t = base.get(rel), ours.get(rel), theirs.get(rel)
        merge = FileMerge(f"{path}/{rel}", b, o, t, o)
        if o == t or b == t:
            pass
        elif b == o:
            merge.result = t
        elif o is None:
            merge.conflicts, merge.why = 1, "deleted in the lab, changed upstream"
        elif t is None:
            merge.conflicts, merge.why = 1, "edited in the lab, deleted or renamed upstream"
        else:
            merged = _merge_file(o.data, b.data if b else b"", t.data)
            if merged is None:
                merge.conflicts, merge.why = 1, "changed on both sides, and git cannot merge it"
            else:
                merge.result, merge.conflicts = Blob(t.mode, merged[0]), merged[1]
        merges.append(merge)
    return merges


def _marked(ours: bytes, theirs: bytes) -> tuple[bytes, int] | None:
    """Every difference between two texts as a conflict, lab text first; None for binary."""
    try:
        a = ours.decode().splitlines(keepends=True)
        b = theirs.decode().splitlines(keepends=True)
    except UnicodeDecodeError:
        return None
    out: list[str] = []
    count = 0

    def chunk(lines: list[str]) -> list[str]:
        return (
            [*lines[:-1], lines[-1] if lines[-1].endswith("\n") else lines[-1] + "\n"]
            if lines
            else []
        )

    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag == "equal":
            out += a[i1:i2]
            continue
        count += 1
        out += [
            "<<<<<<< lab\n",
            *chunk(a[i1:i2]),
            "=======\n",
            *chunk(b[j1:j2]),
            ">>>>>>> upstream\n",
        ]
    return "".join(out).encode(), count


def two_way(path: str, ours: Files, theirs: Files) -> list[FileMerge]:
    """With no pin to merge from, mark every difference between the lab copy and the tip."""
    merges = []
    for rel in sorted(set(ours) | set(theirs)):
        o, t = ours.get(rel), theirs.get(rel)
        merge = FileMerge(f"{path}/{rel}", None, o, t, o)
        if o == t or t is None:
            pass
        elif o is None:
            merge.result = t
        else:
            marked = _marked(o.data, t.data)
            if marked is None:
                merge.conflicts, merge.why = 1, "differs from upstream, and is not text"
            elif marked[1]:
                merge.result, merge.conflicts = Blob(t.mode, marked[0]), marked[1]
            else:
                merge.result = t
        merges.append(merge)
    return merges


@dataclass
class Result:
    """What one pin's sync read and did. The report is rendered from this and the lab checks.

    `files` holds every file of every tracked skill with its three inputs and what was
    written, removed skills included, so a check over the merge needs nothing else.
    """

    upstream: str
    pin: str  # repo-relative path of the pin file
    base: str
    tip: str
    now: Snapshot
    then: Snapshot | None  # None when the pinned commit is gone from the clone
    sync: str = "merge"
    files: list[FileMerge] = field(default_factory=list)
    merged: dict[str, list[FileMerge]] = field(default_factory=dict)  # lab path -> its files
    deleted: list[str] = field(default_factory=list)
    added: list[str] = field(default_factory=list)
    forked: dict[str, str] = field(default_factory=dict)  # lab path -> upstream item
    originals: list[str] = field(default_factory=list)  # what upstream did to each forked one
    mapped: list[str] = field(default_factory=list)  # a review pin's line per item
    cases: list[str] = field(default_factory=list)  # eval cases of skills upstream changed
    notes: list[str] = field(default_factory=list)

    @property
    def pin_lost(self) -> bool:
        """Whether the sync fell back to a two-way diff."""
        return self.then is None

    @property
    def conflicts(self) -> list[FileMerge]:
        """Return the files left with something to resolve."""
        return [f for f in self.files if f.conflicts]


def _short(commit: str) -> str:
    return commit[:7]


def _commits(commits: list[tuple[str, str]]) -> str:
    return "; ".join(f"`{_short(sha)}` {subject}" for sha, subject in commits)


def original(clone: Clone, then: Snapshot | None, now: Snapshot, item: str) -> str:
    """Return what upstream did to a forked item's original between the pin and the tip."""
    if item not in now.skills:
        return "gone upstream."
    if then is None:
        return "not compared: the pin is lost."
    changed = _differing(then.files(item) if item in then.skills else {}, now.files(item))
    if not changed:
        return "unchanged upstream."
    dirs: set[str] = {now.skills[item]}
    if item in then.skills:
        dirs.add(then.skills[item])
    commits = clone.commits(then.commit, now.commit, sorted(dirs))
    return (
        f"upstream changed {', '.join(f'`{rel}`' for rel in changed)} in {len(commits)} "
        f"commit(s): {_commits(commits)}. Port by hand what is worth taking."
    )


def _differing(a: Files, b: Files) -> list[str]:
    return sorted(rel for rel in set(a) | set(b) if a.get(rel) != b.get(rel))


def _start(lab: Lab, pin: Pin, clone: Clone) -> Result:
    """Read both ends of one pin's upstream: its tip, and the pin unless the clone has lost it."""
    tip = clone.tip()
    now = Snapshot(clone, tip, pin.skills_dir)
    then = Snapshot(clone, pin.commit, pin.skills_dir) if clone.has(pin.commit) else None
    rel_pin = pin.path.relative_to(lab.root).as_posix()
    sync = "merge" if pin.merges else "review"
    return Result(pin.upstream, rel_pin, pin.commit, tip, now, then, sync=sync)


def sync_pin(lab: Lab, pin: Pin, clone: Clone, records: dict[str, Any]) -> Result:
    """Merge every skill one merge pin tracks, then move the pin to the tip."""
    result = _start(lab, pin, clone)
    now, then = result.now, result.then
    result.forked = {
        path: source.get("item")
        for path, record in records.items()
        for source in record.get("from", [])
        if source.get("upstream") == pin.upstream
    }
    originals = set(result.forked.values())

    for path, item in sorted(result.forked.items()):
        result.originals.append(f"`{path}`, from `{item}`: {original(clone, then, now, item)}")
        if item not in now.skills:
            result.deleted.append(
                f"`{item}`, the original of forked `{path}`, is gone upstream. The lab copy stays."
            )

    gone: set[str] = set()
    changed: set[str] = set()  # tracked skills whose upstream files moved
    for item, path in sorted(pin.items.items()):
        if path in records:
            result.notes.append(f"`{path}` is tracked and forked at once, so it was not merged.")
            continue
        ours = lab.files(path)
        if item not in now.skills:
            base = then.files(item) if then is not None and item in then.skills else {}
            line = f"`{item}`: gone from upstream's tip, deleted or renamed. Removed `{path}`."
            edited = _differing(base, ours) if then is not None else []
            if edited:
                names = ", ".join(f"`{rel}`" for rel in edited)
                line += f" It carried lab edits in {names}: port them by hand from git."
            result.files += [
                FileMerge(f"{path}/{rel}", base.get(rel), ours.get(rel), None, None)
                for rel in sorted(set(base) | set(ours))
            ]
            lab.remove_skill(path)
            del pin.items[item]
            gone.add(posixpath.basename(path))
            result.deleted.append(line)
            continue
        theirs = now.files(item)
        if then is None or item not in then.skills or then.files(item) != theirs:
            changed.add(posixpath.basename(path))
        if then is None:
            merges = two_way(path, ours, theirs)
            result.notes += [
                f"`{m.path}` is only in the lab copy: a lab page, or a file upstream deleted. "
                "Without the pin the sync cannot tell, so it stays."
                for m in merges
                if m.theirs is None
            ]
        else:
            base = then.files(item) if item in then.skills else {}
            merges = three_way(path, base, ours, theirs)
        for merge in merges:
            if merge.result != merge.ours:
                lab.write(merge.path, merge.result)
        result.files += merges
        result.merged[path] = merges

    arrived: set[str] = set()
    candidates = sorted(now.listed() - set(pin.items) - originals - gone)
    if then is None:
        if candidates:
            names = ", ".join(f"`{n}`" for n in candidates)
            result.notes.append(
                f"Not added, because without the pin a new skill looks like a skipped one: {names}."
            )
    else:
        for name in sorted(set(candidates) - then.listed()):
            path = f"skills/{name}"
            if (lab.root / path).exists():
                result.notes.append(
                    f"`{name}` is new upstream, and `{path}` is taken: map it to another name "
                    "in the pin by hand (docs/adr/0013)."
                )
                continue
            for rel, blob in sorted(now.files(name).items()):
                lab.write(f"{path}/{rel}", blob)
            pin.items[name] = path
            arrived.add(name)
            result.added.append(f"`{name}`: added at `{path}` and mapped in the pin.")

    result.notes += update_gate_lists(lab, arrived, gone)
    names = {posixpath.basename(path) for path in pin.items.values()}
    for case in eval_cases(lab):
        # The longest name wins, so `implement-spec-*` is never `implement`'s case.
        owner = max((n for n in names if case.startswith(n + "-")), key=len, default=None)
        if owner in changed:
            result.cases.append(
                f"`{case}`: upstream changed `{owner}`. A case costs tokens: ask before running it."
            )
    pin.move_to(result.tip)
    return result


def eval_cases(lab: Lab) -> list[str]:
    """Return the case names the shared catalogue lists, in its order; none when it has no list."""
    path = lab.root / EVALS
    match = _CASES_RE.search(path.read_text(encoding="utf-8")) if path.exists() else None
    return match.group(1).split() if match else []


def review_pin(lab: Lab, pin: Pin, clone: Clone) -> Result:
    """Summarise what upstream did to every item one review pin maps, then move the pin.

    An item is named by its path under `skills_dir`. A directory item leaves out the files that
    are items of their own, so a change is counted once.
    """
    result = _start(lab, pin, clone)
    now, then, tip, skills_dir = result.now, result.then, result.tip, pin.skills_dir
    if then is not None:
        for item, target in sorted(pin.items.items()):
            head = f"`{item}`, feeding `{target}`"
            path = f"{skills_dir}/{item}"
            if not clone.exists(tip, path):
                result.mapped.append(f"{head}: gone from upstream's tip, deleted or moved.")
                continue
            inner = [f":(exclude){skills_dir}/{i}" for i in pin.items if i.startswith(item + "/")]
            stat = clone.diffstat(pin.commit, tip, [path, *inner])
            if stat is None:
                result.mapped.append(f"{head}: unchanged.")
                continue
            commits = clone.commits(pin.commit, tip, [path, *inner])
            line = f"{head}: +{stat[0]} -{stat[1]} lines in {len(commits)} commit(s): "
            line += _commits(commits) + "."
            if commits and all(LOW_PRIORITY.search(subject) for _, subject in commits):
                line += " Low priority: model and token cuts only."
            result.mapped.append(line)
        for directory in sorted(now.dirs - then.dirs):
            name = directory.removeprefix(skills_dir + "/")
            if name not in pin.items:
                result.added.append(
                    f"`{name}`: new in {pin.upstream} at `{directory}`. "
                    "Take it as an idea, or leave it."
                )
    pin.move_to(tip)
    return result


# ---------------------------------------------------------------------------------------------
# What a clean merge hides: stale words and dropped edits


def _lines(data: bytes) -> list[str]:
    """Return the lines of a text file, or none for a binary one."""
    return [] if b"\0" in data else data.decode(errors="replace").splitlines()


@dataclass
class Findings:
    """What the two lab checks found for one upstream, as report lines."""

    stale: list[str] = field(default_factory=list)
    dropped: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def removed_words(then: Snapshot, now: Snapshot) -> set[str]:
    """Return the code spans and file names under `skills_dir` at the pin and gone at the tip.

    A word is a name: four characters or more, with a letter and something that is not one,
    such as a dot, slash, hyphen, digit or space. That keeps `CONTEXT.md`, `/grilling` and
    `gh api`, and leaves out `true` and `plan`, which lab prose uses as English.
    """
    gone = then.tokens() - now.tokens()
    return {
        t
        for t in gone
        if len(t) > 3 and any(c.isalpha() for c in t) and not all(c.isalpha() for c in t)
    }


def stale_words(words: set[str], text: list[tuple[str, int, str]]) -> list[str]:
    """Return a report line per removed word the lab text still uses, with where it does."""
    if not words:
        return []
    alternatives = "|".join(re.escape(w) for w in sorted(words, key=lambda w: (-len(w), w)))
    pattern = re.compile(rf"(?<!\w)(?:{alternatives})(?!\w)")
    where: dict[str, list[str]] = {}
    for path, number, line in text:
        for word in dict.fromkeys(m.group(0) for m in pattern.finditer(line)):
            where.setdefault(word, []).append(f"`{path}:{number}`")
    return [f"`{word}` in {', '.join(places)}." for word, places in sorted(where.items())]


def _added(base: Blob | None, ours: Blob) -> list[str]:
    """Return the lines `ours` has that `base` lacks, blank ones left out, each once."""
    new = _lines(ours.data)
    added = new
    if base is not None:
        ops = difflib.SequenceMatcher(None, _lines(base.data), new, autojunk=False).get_opcodes()
        added = [line for tag, _, _, j1, j2 in ops if tag != "equal" for line in new[j1:j2]]
    return list(dict.fromkeys(line for line in added if line.strip()))


def dropped_edits(
    lab: Lab, since: str, before: dict[str, Any], pin: Pin, then: Snapshot
) -> list[str]:
    """Return a report line per line the lab added against the old pin that is gone now.

    A line is kept when any file of its skill still has it. A skill the sync removed keeps its
    lines only in a skill the sync added, which is where a rename's edits are ported.
    """
    arrived = sorted(set(pin.items.values()) - set(before["items"].values()))
    out: list[str] = []
    for item, path in sorted(before["items"].items()):
        pinned = then.files(item) if item in then.skills else {}
        if (lab.root / path).exists():
            kept = lab.lines(path)
        else:
            kept = set().union(*(lab.lines(p) for p in arrived))
        for rel, blob in sorted(lab.files_at(since, path).items()):
            added = _added(pinned.get(rel), blob)
            lost = [line for line in added if line not in kept]
            whole = rel not in pinned and not (lab.root / path / rel).exists()
            if lost and whole and len(lost) == len(added):
                out.append(f"`{path}/{rel}`: a lab file, gone with its {len(lost)} line(s).")
            else:
                out += [f"`{path}/{rel}`: {line}" for line in lost]
    return out


def check_lab(lab: Lab, since: str, clones: dict[str, Clone]) -> dict[str, Findings]:
    """Run the stale-word check for every upstream, and the dropped-edit check for merged ones.

    `since` is the lab as it was before the sync, so its pins name the old commits; the pins on
    disk name the new ones.
    """
    pins = {name: pin for name, pin in lab.pins().items() if name in clones}
    checked = {name: Findings() for name in pins}
    ends: dict[str, tuple[Snapshot | None, Snapshot]] = {}
    for name, pin in pins.items():
        clone, skills_dir = clones[name], pin.skills_dir
        if not clone.has(pin.commit):
            raise RefusalError(f"`{pin.commit}` is not in the clone of `{name}`: clone it again")
        before = lab.pin_at(since, name)
        old = before["commit"] if before else None
        then = Snapshot(clone, old, skills_dir) if old and clone.has(old) else None
        ends[name] = (then, Snapshot(clone, pin.commit, skills_dir))
        merged = pin.merges
        if then is None:
            checked[name].notes.append(
                ("Stale words and dropped edits" if merged else "Stale words")
                + f" not checked: `{_short(old or '')}`, the pin at `{since}`, is not in the clone."
            )
        elif merged and before is not None:
            checked[name].dropped = dropped_edits(lab, since, before, pin, then)

    # A tracked skill's lines that upstream wrote, at either end, are upstream text.
    upstream_text: dict[str, set[str]] = {}
    for name, pin in pins.items():
        if not pin.merges:
            continue
        for item, path in pin.items.items():
            for snapshot in ends[name]:
                if snapshot is not None and item in snapshot.skills:
                    for rel, blob in snapshot.files(item).items():
                        upstream_text.setdefault(f"{path}/{rel}", set()).update(_lines(blob.data))
    text = [
        (path, number, line)
        for path in lab.text_paths()
        for number, line in enumerate(_lines((lab.root / path).read_bytes()), 1)
        if line not in upstream_text.get(path, ())
    ]
    for name, (then, now) in ends.items():
        if then is not None:
            checked[name].stale = stale_words(removed_words(then, now), text)
    return checked


# ---------------------------------------------------------------------------------------------
# The report


def _section(title: str, lines: list[str]) -> list[str]:
    return [f"### {title}", "", *(f"- {line}" for line in lines), ""] if lines else []


def render(results: list[Result], checked: dict[str, Findings]) -> str:
    """Return the report in Markdown, so it can go into the pull request as it is."""
    out = ["# Upstream sync", ""]
    for r in results:
        found = checked.get(r.upstream, Findings())
        out += [f"## {r.upstream}: `{_short(r.base)}` to `{_short(r.tip)}`", ""]
        moved = f"moved from `{_short(r.base)}` to `{_short(r.tip)}`"
        stayed = f"stays at `{_short(r.tip)}`: upstream has not moved"
        pin = _section("Pin", [f"`{r.pin}` {moved if r.base != r.tip else stayed}."])
        if r.sync == "review":
            lost = (
                f"`{_short(r.base)}` is not in the clone: upstream rewrote its history, so nothing "
                "could be compared. Read the mapped items at the tip by hand."
            )
            out += _section("Pin lost", [lost] if r.pin_lost else [])
            out += _section("Stale words", found.stale)
            out += _section("Mapped items", r.mapped)
            out += _section("New skills", r.added)
            out += _section("Notes", r.notes + found.notes)
            out += pin
            continue
        if r.pin_lost:
            out += _section(
                "Pin lost",
                [
                    f"`{_short(r.base)}` is not in the clone: upstream rewrote its history. This "
                    "sync fell back to a two-way diff. Every difference between a lab copy and "
                    "upstream's tip is marked as a conflict, the lab's text first. Keep the "
                    "lab's edits and take upstream's text."
                ],
            )
        conflicts = []
        for f in r.conflicts:
            if f.why:
                conflicts.append(f"`{f.path}`: {f.why}. The lab's copy is in place.")
            else:
                conflicts.append(f"`{f.path}`: {f.conflicts} conflict(s) between the markers.")
        out += _section("Conflicts", conflicts)
        out += _section("Dropped edits", found.dropped)
        out += _section("Stale words", found.stale)
        out += _section("Deleted upstream", r.deleted)
        out += _section("New skills", r.added)
        out += _section("Forked, not merged", r.originals)
        merged = []
        for path, merges in sorted(r.merged.items()):
            changed = sum(1 for m in merges if m.result != m.ours)
            merged.append(
                f"`{path}`: {changed} file(s) changed." if changed else f"`{path}`: unchanged."
            )
        out += _section("Merged", merged)
        out += _section("Eval cases to rerun", r.cases)
        out += _section("Notes", r.notes + found.notes)
        out += pin
    return "\n".join(out).rstrip() + "\n"


# ---------------------------------------------------------------------------------------------
# Commands


def _clones(specs: list[str], pins: dict[str, Pin]) -> dict[str, Clone]:
    clones: dict[str, Clone] = {}
    for spec in specs:
        name, sep, path = spec.partition("=")
        if not sep or not name or not path:
            raise RefusalError(f"--clone takes NAME=DIR, not `{spec}`")
        if name not in pins:
            raise RefusalError(f"--clone names `{name}`, and there is no upstream/{name}/pin.json")
        clones[name] = Clone(Path(path).resolve())
    for name, pin in pins.items():
        if name not in clones:
            raise RefusalError(
                f"no clone of `{name}`: run `git clone {pin.repo} <dir>`, then pass "
                f"`--clone {name}=<dir>`"
            )
    return clones


def merge(lab: Lab, specs: list[str]) -> int:
    """Run the merge for every merge pin, print the report, and return the exit status."""
    pins = lab.pins()
    clones = _clones(specs, pins)
    lab.require_clean()
    records = lab.attribution()
    results = [
        sync_pin(lab, pin, clones[name], records)
        if pin.merges
        else review_pin(lab, pin, clones[name])
        for name, pin in sorted(pins.items())
    ]
    print(render(results, check_lab(lab, "HEAD", clones)), end="")
    return 1 if any(r.conflicts for r in results) else 0


def recheck(lab: Lab, specs: list[str], since: str) -> int:
    """Rerun the stale-word and dropped-edit checks on the tree as it stands; 1 if either finds."""
    if _git(
        lab.root, "rev-parse", "--verify", "--quiet", f"{since}^{{commit}}", check=False
    ).returncode:
        raise RefusalError(f"`{since}` is not a commit in {lab.root}")
    checked = check_lab(lab, since, _clones(specs, lab.pins()))
    out = [f"# Upstream sync: recheck against `{since}`", ""]
    for name, found in sorted(checked.items()):
        body = _section("Dropped edits", found.dropped) + _section("Stale words", found.stale)
        out += [f"## {name}", "", *(body or ["Nothing to report.", ""])]
        out += _section("Notes", found.notes)
    print("\n".join(out).rstrip() + "\n", end="")
    return 1 if any(found.dropped or found.stale for found in checked.values()) else 0


def fork(lab: Lab, name: str, changes: str | None) -> int:
    """Move tracked skill `name` from its pin's name map to an attribution record."""
    path = f"skills/{name}"
    tracked = [
        (pin, item)
        for pin in lab.pins().values()
        if pin.merges
        for item, mapped in pin.items.items()
        if mapped == path
    ]
    if not tracked:
        raise RefusalError(f"`{path}` is not a tracked skill: no merge pin maps it")
    records = lab.attribution()
    if path in records:
        raise RefusalError(f"`{path}` already has an attribution record")
    pin, item = tracked[0]
    record: dict[str, Any] = {
        "from": [{"upstream": pin.upstream, "item": item, "commit": pin.commit}]
    }
    if changes:
        record["changes"] = changes
    del pin.items[item]
    pin.save()
    records[path] = record
    lab.save_attribution(records)
    print(
        f"Forked `{path}`: removed `{item}` from upstream/{pin.upstream}/pin.json and recorded it "
        f"in {ATTRIBUTION} at `{_short(pin.commit)}`. Commit this on its own."
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    """Parse the command line, run one command, and return its exit status."""
    parser = argparse.ArgumentParser(
        prog="upstream_sync.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--lab", type=Path, default=Path(), help="the lab tree (default: .)")
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("merge", help="merge every tracked skill from its pin to the tip")
    run.add_argument(
        "--clone",
        action="append",
        default=[],
        metavar="NAME=DIR",
        help="a fresh clone of upstream NAME; one per merged upstream",
    )
    run.add_argument("--lab", type=Path, default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    again = commands.add_parser(
        "recheck", help="rerun the stale-word and dropped-edit checks once conflicts are resolved"
    )
    again.add_argument("--clone", action="append", default=[], metavar="NAME=DIR")
    again.add_argument(
        "--since", default="HEAD", help="the lab before the sync (default: HEAD, uncommitted)"
    )
    again.add_argument("--lab", type=Path, default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    split = commands.add_parser("fork", help="make a tracked skill lab-owned")
    split.add_argument("name", help="the skill's directory name under skills/")
    split.add_argument("--changes", help="one line on what the lab changes, for the record")
    split.add_argument("--lab", type=Path, default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    lab = Lab(args.lab.resolve())
    try:
        if args.command == "merge":
            return merge(lab, args.clone)
        if args.command == "recheck":
            return recheck(lab, args.clone, args.since)
        return fork(lab, args.name, args.changes)
    except RefusalError as e:
        print(f"upstream_sync: refused, nothing written: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
