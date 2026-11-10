"""Set a machine up so Claude Code, Codex and Kimi Code all follow the `lab` plugin.

The mechanical half of `/lab-setup`. Each step below is one function that reads the machine,
and changes it only if it is not already set up; the skill decides with the member which steps
run. It removes nothing, leaves alone any entry it did not write, and a second run on a set-up
machine changes no file. See `docs/adr/0014-installed-copies-update-on-their-own.md`.

    python3 lab_setup.py --home "$HOME" [--dry-run] [--only STEP ...]

Every path it reads or writes comes from `--home`, never from `$HOME`, so a test can hand it a
fake one; only PATH is read from the environment, to find `codex` and a user bin folder. It
imports only the standard library and runs on Python 3.11 or newer (`tomllib`), because a
fresh machine has no pixi environment to run it in. Exit: 0 done, 1 refused or a step failed,
2 usage.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Literal

MARKETPLACE = "liulab"
PLUGIN = f"lab@{MARKETPLACE}"
REPO = "liuhlab/liulab-skills"
# Written with `~/`, which Kimi expands against the home itself (`resolveConfiguredDir` in its
# skill catalogue), so the file carries no username.
KIMI_ENTRY = f"~/.claude/plugins/marketplaces/{MARKETPLACE}/skills"
# The lab defaults page, by its path in the marketplace clone. The marked block points each
# agent's user-level instructions file at it, so an edit to the page reaches every machine with
# the next plugin update and no rerun. Claude Code loads a bare `@~/` line in `~/.claude/CLAUDE.md`
# as an import; Codex and Kimi Code read the same line as a path to open.
DEFAULTS_PAGE = "skills/lab-setup/references/defaults.md"
BEGIN = "<!-- BEGIN lab defaults: /lab-setup writes this block and replaces it on a rerun -->"
END = "<!-- END lab defaults -->"
BLOCK = f"""{BEGIN}
## Lab defaults

Before the first tool call of a session, read the lab defaults page below: the issue tracker,
triage labels and domain docs every lab repo gets, and the lab's always-on rules. A repo's own
`docs/agents/` page overrides only the default it covers.

@~/.claude/plugins/marketplaces/{MARKETPLACE}/{DEFAULTS_PAGE}
{END}
"""
# The user bin folders a launcher's link may go in, preferred first. Only these: PATH also
# holds folders under the home that belong to a tool, such as this plugin's own `bin/` in Claude
# Code's cache or Kimi's `~/.kimi-code/bin`, and a link there would vanish with the tool.
BIN_FOLDERS = (".local/bin", "bin")


@dataclass(frozen=True)
class Machine:
    """The machine a run acts on, every path derived from the home it was given."""

    home: Path
    codex_home: Path
    kimi_home: Path
    path: tuple[str, ...]
    dry_run: bool

    @property
    def clone(self) -> Path:
        """Claude Code's git clone of the `liulab` marketplace."""
        return self.home / ".claude" / "plugins" / "marketplaces" / MARKETPLACE

    def show(self, path: Path) -> str:
        """Spell a path with the home collapsed to `~`: an absolute home carries a username."""
        text = str(path)
        home = str(self.home)
        return "~" + text[len(home) :] if text == home or text.startswith(home + os.sep) else text


#: What a step found or did, the report's first column. Only `failed` makes the run exit 1.
Status = Literal["ok", "changed", "would change", "skipped", "failed", "clash"]


@dataclass(frozen=True)
class Line:
    """One line of the report: what a step found or did."""

    status: Status
    step: str
    detail: str

    def __str__(self) -> str:
        """Render as an aligned row."""
        return f"{self.status:<13}{self.step:<12}{self.detail}"


def claude(machine: Machine) -> list[Line]:
    """Turn on `autoUpdate` for the `liulab` entry in Claude Code's user settings."""
    step = "claude"
    path = machine.home / ".claude" / "settings.json"
    shown = machine.show(path)
    try:
        settings = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except json.JSONDecodeError as error:
        return [Line("failed", step, f"{shown} is not valid JSON ({error}); left alone")]
    markets = settings.get("extraKnownMarketplaces", {}) if isinstance(settings, dict) else None
    entry = markets.get(MARKETPLACE) if isinstance(markets, dict) else None
    if not isinstance(markets, dict) or not isinstance(entry, dict | None):
        return [Line("failed", step, f"{shown} has an unexpected shape; left alone")]
    if entry is not None and entry.get("autoUpdate") is True:
        return [Line("ok", step, f"auto-update is on for {MARKETPLACE} in {shown}")]
    # Kept whole when it is there: its source is whatever the member's install wrote.
    turned_on: dict[str, object] = {"source": {"source": "github", "repo": REPO}, **(entry or {})}
    turned_on["autoUpdate"] = True
    if machine.dry_run:
        return [Line("would change", step, f"turn on auto-update for {MARKETPLACE} in {shown}")]
    markets[MARKETPLACE] = turned_on
    settings["extraKnownMarketplaces"] = markets
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(settings, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return [Line("changed", step, f"turned on auto-update for {MARKETPLACE} in {shown}")]


def read_toml(path: Path) -> dict[str, object]:
    """Parse a TOML file, an absent one as empty. Raises `tomllib.TOMLDecodeError`."""
    return tomllib.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def codex(machine: Machine) -> list[Line]:
    """Install the `lab` plugin with Codex's own commands, running only what is not done."""
    step = "codex"
    config = machine.codex_home / "config.toml"
    try:
        data = read_toml(config)
    except tomllib.TOMLDecodeError as error:
        return [Line("failed", step, f"{machine.show(config)} is not valid TOML ({error})")]
    markets, plugins = data.get("marketplaces", {}), data.get("plugins", {})
    runs: list[list[str]] = []
    if not (isinstance(markets, dict) and MARKETPLACE in markets):
        runs.append(["plugin", "marketplace", "add", REPO])
    if not (isinstance(plugins, dict) and PLUGIN in plugins):
        runs.append(["plugin", "add", PLUGIN])
    if not runs:
        return [Line("ok", step, f"{PLUGIN} is installed in Codex")]
    program = shutil.which("codex", path=os.pathsep.join(machine.path))
    if program is None:
        return [Line("skipped", step, "no codex command on PATH, so Codex was not set up")]
    said = "; ".join("codex " + " ".join(args) for args in runs)
    if machine.dry_run:
        return [Line("would change", step, f"run {said}")]
    env = {**os.environ, "HOME": str(machine.home), "CODEX_HOME": str(machine.codex_home)}
    for args in runs:
        done = subprocess.run(
            [program, *args], env=env, capture_output=True, text=True, check=False
        )
        if done.returncode != 0:
            output = (done.stderr or done.stdout).strip().splitlines()
            reason = output[-1] if output else f"exit status {done.returncode}"
            return [Line("failed", step, f"codex {' '.join(args)}: {reason}")]
    return [Line("changed", step, f"installed {PLUGIN} in Codex ({said})")]


def expand(folder: str, home: Path) -> Path:
    """Resolve a configured folder the way Kimi does: a leading `~/` means the home."""
    if folder == "~" or folder.startswith("~/"):
        return home / folder[2:]
    return Path(folder)


def same(one: Path, other: Path) -> bool:
    """Say whether two spellings name one folder, without asking the disk."""
    return os.path.normpath(one) == os.path.normpath(other)


_TABLE = re.compile(r"^[ \t]*\[", re.MULTILINE)
_SKILL_DIRS = re.compile(r"^[ \t]*extra_skill_dirs[ \t]*=[ \t]*\[", re.MULTILINE)


def array_end(text: str, start: int) -> tuple[int, int, str]:
    """Find the `]` closing the TOML array whose `[` ends at `start`.

    Returns its index, the index just past the last value or comma inside the array, and
    that character (`[` for an empty array). Strings and comments are stepped over, so a `]`,
    `,` or `#` inside either does not count. Raises `ValueError` if the array never closes.
    """
    depth, i, after, last = 1, start, start, "["
    while i < len(text):
        char = text[i]
        if char == "#":
            end = text.find("\n", i)
            i = len(text) if end < 0 else end
            continue
        if char in "\"'":
            quote = text[i : i + 3] if text[i : i + 3] in ('"""', "'''") else char
            j = i + len(quote)
            while j < len(text) and not text.startswith(quote, j):
                j += 2 if quote[0] == '"' and text[j] == "\\" else 1
            i = after = j + len(quote)
            last = '"'
            continue
        if char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
            if depth == 0:
                return i, after, last
        if not char.isspace():
            after, last = i + 1, char
        i += 1
    raise ValueError("the extra_skill_dirs array never closes")


def add_folder(text: str, folder: str) -> str:
    """Add `folder` to the top-level `extra_skill_dirs` array in the TOML `text`.

    A text edit, so the member's comments, spacing and order survive: the standard library
    reads TOML but cannot write it. The caller re-reads the result to prove that nothing but
    the one entry changed.
    """
    value = json.dumps(folder)
    table = _TABLE.search(text)
    top = text[: table.start()] if table else text
    key = _SKILL_DIRS.search(top)
    if key is None:
        # A top-level key written below a table header would belong to that table.
        line = f"extra_skill_dirs = [{value}]\n"
        if table:
            return text[: table.start()] + line + text[table.start() :]
        return text + ("\n" if text and not text.endswith("\n") else "") + line
    close, after, last = array_end(text, key.end())
    line_start = text.rfind("\n", 0, close) + 1
    if line_start > after and not text[line_start:close].strip():
        # `]` on a line of its own: one value per line, so the entry gets a line above it.
        value_line = text[text.rfind("\n", 0, after) + 1 : after]
        indent = value_line[: len(value_line) - len(value_line.lstrip(" \t"))]
        indent = "  " if last == "[" else indent
        comma = "" if last in "[," else ","
        line = f"{indent}{value}{',' if last == ',' else ''}\n"
        return text[:after] + comma + text[after:line_start] + line + text[line_start:]
    joint = "" if last == "[" else " " if last == "," else ", "
    return text[:after] + joint + value + text[after:]


def kimi(machine: Machine) -> list[Line]:
    """Add the marketplace clone's skills folder to Kimi Code's `extra_skill_dirs`."""
    step = "kimi"
    if not machine.kimi_home.is_dir():
        shown = machine.show(machine.kimi_home)
        return [Line("skipped", step, f"no Kimi Code home at {shown}, so Kimi was not set up")]
    path = machine.kimi_home / "config.toml"
    shown = machine.show(path)
    try:
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        return [Line("failed", step, f"{shown} is not valid TOML ({error}); left alone")]
    folders = data.get("extra_skill_dirs", [])
    if not (isinstance(folders, list) and all(isinstance(f, str) for f in folders)):
        return [Line("failed", step, f"extra_skill_dirs in {shown} is not a list of folders")]
    skills = machine.clone / "skills"
    if any(same(expand(folder, machine.home), skills) for folder in folders):
        return [Line("ok", step, f"Kimi reads the clone's skills ({shown})")]
    try:
        new = add_folder(text, KIMI_ENTRY)
        proven = tomllib.loads(new) == {**data, "extra_skill_dirs": [*folders, KIMI_ENTRY]}
    except ValueError:  # `TOMLDecodeError` is one
        new, proven = "", False
    if not proven:
        return [Line("failed", step, f"add {KIMI_ENTRY} to extra_skill_dirs in {shown} by hand")]
    if machine.dry_run:
        return [Line("would change", step, f"add {KIMI_ENTRY} to extra_skill_dirs in {shown}")]
    path.write_text(new, encoding="utf-8")
    return [Line("changed", step, f"added {KIMI_ENTRY} to extra_skill_dirs in {shown}")]


# The begin marker is matched by its prefix, so a later release can reword the rest of it and
# still find the block an earlier one wrote.
_BEGIN = re.compile(r"^<!-- BEGIN lab defaults\b.*(?:\n|$)", re.MULTILINE)
_END = re.compile(r"^<!-- END lab defaults -->[ \t]*(?:\n|$)", re.MULTILINE)


def with_block(text: str) -> str:
    """Return `text` holding the current block once: in place of the old one, else at the end.

    Everything outside the markers is kept byte for byte. Raises `ValueError` when the markers
    are not one begin followed by one end: what lies between them is then not knowably the
    block, and replacing it could take the member's own text with it.
    """
    begins, ends = list(_BEGIN.finditer(text)), list(_END.finditer(text))
    if len(begins) == len(ends) == 1 and begins[0].start() < ends[0].start():
        return text[: begins[0].start()] + BLOCK + text[ends[0].end() :]
    if begins or ends:
        raise ValueError(
            f"has {len(begins)} begin and {len(ends)} end markers of the lab defaults block,"
            " not one pair; keep one pair or none"
        )
    if not text:
        return BLOCK
    return text + ("" if text.endswith("\n") else "\n") + "\n" + BLOCK


def point(machine: Machine, step: str, agent: str, path: Path) -> Line:
    """Write the marked block into one agent's instructions file, unless it is there already."""
    shown = machine.show(path)
    try:
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        new = with_block(text)
    except (OSError, UnicodeDecodeError) as error:
        return Line("failed", step, f"{shown} could not be read ({error}); left alone")
    except ValueError as error:
        return Line("failed", step, f"{shown} {error}; left alone")
    if new == text:
        return Line("ok", step, f"{shown} points {agent} at the lab defaults")
    do, done = ("replace", "replaced") if _BEGIN.search(text) else ("add", "added")
    if machine.dry_run:
        return Line("would change", step, f"{do} the lab defaults block in {shown}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(new, encoding="utf-8")
    return Line("changed", step, f"{done} the lab defaults block in {shown}")


def defaults(machine: Machine) -> list[Line]:
    """Point each agent's user-level instructions file at the lab defaults page."""
    step = "defaults"
    codex_found = machine.codex_home.is_dir() or bool(
        shutil.which("codex", path=os.pathsep.join(machine.path))
    )
    # Codex reads the first of these two that has text, so while the override has any, the
    # block in `AGENTS.md` is never read.
    override = machine.codex_home / "AGENTS.override.md"
    shadowed = override.is_file() and bool(override.read_text(errors="replace").strip())
    codex_aside = f"; but Codex reads {machine.show(override)} instead while it has text"
    targets = (
        ("Claude Code", machine.home / ".claude" / "CLAUDE.md", True, ""),
        ("Codex", machine.codex_home / "AGENTS.md", codex_found, codex_aside if shadowed else ""),
        ("Kimi Code", machine.kimi_home / "AGENTS.md", machine.kimi_home.is_dir(), ""),
    )
    lines: list[Line] = []
    for agent, path, present, aside in targets:
        if not present:
            detail = f"no {agent} on this machine, so it was not pointed anywhere"
            lines.append(Line("skipped", step, detail))
            continue
        line = point(machine, step, agent, path)
        lines.append(replace(line, detail=line.detail + aside))
    return lines


def launcher_link(machine: Machine, step: str) -> list[Line]:
    """Link the clone's launcher named `step` into a user bin folder already on PATH."""
    launcher = machine.clone / "bin" / step
    if not launcher.is_file():
        return [Line("skipped", step, f"the marketplace clone has no bin/{step}")]
    folders = [machine.home / name for name in BIN_FOLDERS]
    folder = next(
        (f for f in folders if f.is_dir() and any(same(f, Path(p)) for p in machine.path if p)),
        None,
    )
    if folder is None:
        names = " nor ".join(machine.show(f) for f in folders)
        return [Line("skipped", step, f"neither {names} is a folder on PATH; no link made")]
    link = folder / step
    shown = machine.show(link)
    if link.is_symlink() and link.resolve() == launcher.resolve():
        return [Line("ok", step, f"{shown} links to the marketplace clone")]
    if link.is_symlink() or link.exists():
        return [Line("skipped", step, f"{shown} is already something else; left alone")]
    if machine.dry_run:
        return [Line("would change", step, f"link {shown} to the marketplace clone")]
    link.symlink_to(launcher)
    return [Line("changed", step, f"linked {shown} to the marketplace clone")]


def edison(machine: Machine) -> list[Line]:
    """Link the clone's `edison-cli` launcher into a user bin folder already on PATH."""
    return launcher_link(machine, "edison-cli")


def lab_deck(machine: Machine) -> list[Line]:
    """Link the clone's `lab-deck` launcher into a user bin folder already on PATH."""
    return launcher_link(machine, "lab-deck")


def declared_name(folder: Path) -> str | None:
    """Read the `name:` a skill's frontmatter declares, if it declares one."""
    try:
        text = (folder / "SKILL.md").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    front = re.match(r"---[ \t]*\n(.*?)\n---", text, re.DOTALL)
    name = re.search(r"^name:[ \t]*['\"]?([^'\"\s]+)", front[1], re.MULTILINE) if front else None
    return name[1] if name else None


def clashes(machine: Machine) -> list[Line]:
    """List every user-level skill that takes a name the plugin ships. Changes nothing."""
    step = "clashes"
    shipped_from = machine.clone / "skills"
    shipped = {d.name for d in shipped_from.iterdir() if (d / "SKILL.md").is_file()}
    # The folders the three agents read skills from at the user level, then Kimi's own extras.
    folders = [
        machine.home / ".claude" / "skills",
        machine.home / ".agents" / "skills",
        machine.codex_home / "skills",
        machine.kimi_home / "skills",
    ]
    try:
        extra = read_toml(machine.kimi_home / "config.toml").get("extra_skill_dirs", [])
    except tomllib.TOMLDecodeError:
        extra = []  # the kimi step reports the broken file
    if isinstance(extra, list):
        # A relative entry is read against whichever repo Kimi starts in, so it has no one home.
        named = [f for f in extra if isinstance(f, str) and (f.startswith("~") or f[:1] == "/")]
        folders += [expand(f, machine.home) for f in named]
    lines: list[Line] = []
    seen: set[str] = set()
    for folder in folders:
        key = os.path.normpath(folder)
        if key in seen or same(folder, shipped_from) or not folder.is_dir():
            continue
        seen.add(key)
        for skill in sorted(folder.iterdir()):
            if not (skill / "SKILL.md").is_file():
                continue
            # Codex and Kimi go by the declared name; the folder's name counts as well.
            taken = sorted({skill.name, declared_name(skill) or skill.name} & shipped)
            if taken:
                detail = f"{machine.show(skill)} takes the shipped name {', '.join(taken)}"
                lines.append(Line("clash", step, detail))
    return lines or [Line("ok", step, "no user-level skill takes a name the plugin ships")]


# One entry per step, in the order a full run takes them. A new step is one function and one
# line here; `--only` and the report pick it up from this table.
STEPS: dict[str, Callable[[Machine], list[Line]]] = {
    "claude": claude,
    "codex": codex,
    "kimi": kimi,
    "defaults": defaults,
    "edison-cli": edison,
    "lab-deck": lab_deck,
    "clashes": clashes,
}


def main(argv: list[str] | None = None) -> int:
    """Run the chosen steps on the machine at `--home` and print one line per finding."""
    parser = argparse.ArgumentParser(description="Set a machine up to follow the lab plugin.")
    parser.add_argument("--home", required=True, type=Path, help="the home directory to set up")
    parser.add_argument("--codex-home", type=Path, help="Codex's home (default: HOME/.codex)")
    parser.add_argument("--kimi-home", type=Path, help="Kimi's home (default: HOME/.kimi-code)")
    parser.add_argument("--dry-run", action="store_true", help="report, and change nothing")
    parser.add_argument("--only", action="append", choices=list(STEPS), help="run this step")
    args = parser.parse_args(argv)
    home = args.home.absolute()
    machine = Machine(
        home=home,
        codex_home=(args.codex_home or home / ".codex").absolute(),
        kimi_home=(args.kimi_home or home / ".kimi-code").absolute(),
        path=tuple(os.environ.get("PATH", "").split(os.pathsep)),
        dry_run=args.dry_run,
    )

    # Kimi reads its skills from the clone and the launcher links point into it, so with no
    # clone there is nothing to point anything at. Checked before any step, so nothing changes.
    if not (machine.clone / "skills").is_dir():
        print(f"refused: no marketplace clone at {machine.show(machine.clone)}; nothing changed.")
        print(f"Install the plugin first: claude plugin marketplace add {REPO}, then")
        print(f"claude plugin install {PLUGIN}. If it is installed, Claude Code keeps its clone")
        print("somewhere else now, and this script needs updating before Kimi can follow it.")
        return 1

    lines = [line for name in args.only or STEPS for line in STEPS[name](machine)]
    for line in lines:
        print(line)
    return 1 if any(line.status == "failed" for line in lines) else 0


if __name__ == "__main__":
    sys.exit(main())
