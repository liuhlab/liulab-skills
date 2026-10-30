"""Install, verify and run a selected agent against the shared eval catalogue."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
CODEX_CASES = {"lab-hpc-data-job-planning", "explicit", "trigger", "reject", "edison-kosmos"}


def run(command: list[str], env: dict[str, str], cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run one checked setup operation without leaking its output on success."""
    result = subprocess.run(command, env=env, cwd=cwd, capture_output=True, text=True, check=False)
    if result.returncode:
        raise RuntimeError(
            f"setup failed: {command[0]} {' '.join(command[1:3])}, exit {result.returncode}"
        )
    return result


def content(root: Path, paths: list[str]) -> str:
    """Hash the shipped files and their relative names, rejecting missing content."""
    digest = hashlib.sha256()
    for name in paths:
        path = root / name
        if not path.is_file():
            raise RuntimeError(f"content verification failed: missing {name}")
        digest.update(name.encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
    return digest.hexdigest()


def installed_root(home: Path, expected: str, paths: list[str]) -> Path:
    """Find a single installed lab plugin whose entire shipped content matches."""
    matches = []
    for manifest in home.glob("**/cache/**/.claude-plugin/plugin.json"):
        root = manifest.parent.parent
        try:
            if content(root, paths) == expected:
                matches.append(root)
        except RuntimeError:
            continue
    if len(matches) != 1:
        raise RuntimeError(
            "content verification failed: expected exactly one matching installed plugin"
        )
    return matches[0]


def setup(agent: str, directory: Path) -> dict[str, Any]:
    """Create only run-owned agent state and verify the installed snapshot."""
    snapshot = directory / "source"
    snapshot.mkdir()
    paths = (
        subprocess.check_output(
            ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], cwd=REPO
        )
        .decode()
        .split("\0")
    )
    paths = sorted(name for name in paths if name and (REPO / name).is_file())
    for name in paths:
        target = snapshot / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / name, target)
    expected = content(snapshot, paths)
    home = directory / "agent-home"
    home.mkdir(mode=0o700)
    env = dict(os.environ)
    commands = []
    if agent == "codex":
        original = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
        auth = original / "auth.json"
        if auth.is_file():
            (home / "auth.json").symlink_to(auth)
        config_path = original / "config.toml"
        if config_path.is_file():
            # Copy only simple scalar model settings, never marketplaces or hooks.
            inherited = re.findall(
                r'^((?:model|model_reasoning_effort)\s*=\s*["\'][A-Za-z0-9_.:/-]+["\'])\s*$',
                config_path.read_text().split("\n[", 1)[0],
                re.MULTILINE,
            )
            (home / "config.toml").write_text("\n".join(inherited) + "\n")
        env["CODEX_HOME"] = str(home)
        commands = [
            ["codex", "plugin", "marketplace", "add", str(snapshot)],
            ["codex", "plugin", "add", "lab@liulab", "--json"],
        ]
    else:
        original = Path(os.environ.get("CLAUDE_CONFIG_DIR", str(Path.home() / ".claude")))
        auth = original / ".credentials.json"
        if auth.is_file():
            (home / ".credentials.json").symlink_to(auth)
        env["CLAUDE_CONFIG_DIR"] = str(home)
        commands = [
            ["claude", "plugin", "marketplace", "add", str(snapshot)],
            ["claude", "plugin", "install", "lab@liulab"],
        ]
    for command in commands:
        run(command, env, directory)
    root = installed_root(home, expected, paths)
    return {
        "agent": agent,
        "env": {"CODEX_HOME" if agent == "codex" else "CLAUDE_CONFIG_DIR": str(home)},
        "plugin_root": str(root),
        "content_sha256": expected,
        "version": json.loads((root / ".claude-plugin/plugin.json").read_text())["version"],
        "source_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=REPO, text=True
        ).strip(),
        "source_dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=REPO)),
        "installation_changes": "run-owned agent home and snapshot only",
    }


def launch(args: list[str]) -> int:
    """Translate the catalogue invocation to the selected agent's headless interface."""
    context = json.loads(Path(os.environ["LAB_EVAL_CONTEXT"]).read_text())
    prompt, *flags = args
    agent = context["agent"]
    env = {**os.environ, **context["env"]}
    root = Path(context["plugin_root"])
    if agent == "codex":
        prompt = prompt.replace("/lab-hpc", "$lab-hpc").replace("/lab-edison", "$lab-edison")
        prompt += f"\nUse the installed lab plugin at {root}. Read its skill text from that cache. Plan only; do not run cluster commands, submit jobs, or write files."
        command = [
            "codex",
            "--no-daemon",
            "-a",
            "never",
            "exec",
            "--sandbox",
            "read-only",
            "--json",
            "--skip-git-repo-check",
            prompt,
        ]
    else:
        command = ["claude", "-p", prompt, *flags, "--output-format", "stream-json", "--verbose"]
    return subprocess.run(
        command, env=env, cwd=Path(os.environ["LAB_EVAL_WORKSPACE"]), check=False
    ).returncode


class SelectionParser(argparse.ArgumentParser):
    """Explain that selection errors happen before any paid or mutating operation."""

    def error(self, message: str) -> None:
        """Keep the public guard's no-spend refusal visible."""
        print("Nothing was run and nothing was spent.", file=sys.stderr)
        super().error(message)


def main() -> int:
    """Validate selection before creating state or spending tokens."""
    if sys.argv[1:2] == ["launch"]:
        return launch(sys.argv[2:])
    parser = SelectionParser()
    parser.add_argument("--agent", required=True)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--only")
    selection.add_argument("--all", action="store_true")
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    if args.agent not in {"codex", "claude"}:
        parser.error(f"unsupported agent: {args.agent}")
    catalogue = subprocess.check_output(
        ["bash", str(REPO / "tests/eval_cases.sh"), "--dump"], text=True
    )
    cases = {row.split("\x1f")[0] for row in catalogue.splitlines()}
    if args.only is not None and args.only not in cases:
        parser.error(f"unsupported case: {args.only}")
    if args.agent == "codex" and (args.all or args.live or args.only not in CODEX_CASES):
        parser.error(
            "unsupported Codex case selection; supported: " + ", ".join(sorted(CODEX_CASES))
        )
    directory = Path(tempfile.mkdtemp(prefix="lab-agent-eval-"))
    directory.chmod(0o700)
    evidence: dict[str, Any] = {
        "agent": args.agent,
        "case": args.only if args.only is not None else "all",
        "stage": "setup",
        "result": "incomplete",
    }
    evidence_path = directory / "evidence.json"
    print(f"agent: {args.agent}\nevidence: {evidence_path}", flush=True)
    try:
        context = setup(args.agent, directory)
        evidence.update({key: value for key, value in context.items() if key != "env"})
        evidence["content_verified"] = True
        evidence["stage"] = "evaluation"
        context_path = directory / "context.json"
        context_path.write_text(json.dumps(context))
        workspace = directory / "workspace"
        workspace.mkdir()
        env = {
            **os.environ,
            "LAB_EVAL_CONTEXT": str(context_path),
            "LAB_EVAL_WORKSPACE": str(workspace),
            "TMPDIR": str(directory),
        }
        flags = ["--only", args.only] if args.only is not None else ["--all"]
        if args.live:
            flags.append("--live")
        result = subprocess.run(
            ["bash", str(directory / "source/tests/eval_cases.sh"), *flags], env=env, check=False
        )
        evidence["assertions"] = "pass" if result.returncode == 0 else "fail"
        evidence["result"] = evidence["assertions"]
        evidence["stage"] = "complete"
        evidence["transcripts"] = [str(path) for path in directory.glob("lab-skill-eval.*/*.txt")]
        evidence["transcript_review"] = "required before claiming behavioral verification"
        return result.returncode
    except (RuntimeError, OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        evidence["error"] = str(error)
        return 1
    finally:
        evidence_path.write_text(json.dumps(evidence, indent=2) + "\n")
        # Authentication links are not part of the retained evidence.
        for name in ("auth.json", ".credentials.json"):
            auth_link = directory / "agent-home" / name
            if auth_link.is_symlink():
                auth_link.unlink()


if __name__ == "__main__":
    sys.exit(main())
