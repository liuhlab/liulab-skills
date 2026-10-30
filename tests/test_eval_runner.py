"""Exercise eval selection and failed runner handling without paid sessions."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def test_unknown_agent_never_launches(tmp_path: Path) -> None:
    """An unknown runner is rejected before any installation or eval."""
    stub = tmp_path / "codex"
    calls = tmp_path / "calls"
    stub.write_text(f"#!/bin/sh\necho called >> '{calls}'\n")
    stub.chmod(0o755)
    result = subprocess.run(
        ["bash", "tests/eval.sh", "--agent", "unknown", "--only", "explicit"],
        cwd=REPO,
        env={**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}"},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert "unsupported agent" in result.stderr
    assert not calls.exists()


def stub_agent(tmp_path: Path) -> tuple[dict[str, str], Path]:
    """Create a fake installer and runner that only touches its run-owned home."""
    bindir = tmp_path / "bin"
    bindir.mkdir()
    calls = tmp_path / "calls"
    script = """#!/usr/bin/env python3
import json, os, pathlib, shutil, sys
args = sys.argv[1:]
with open(os.environ['STUB_CALLS'], 'a') as f:
    f.write(json.dumps([pathlib.Path(sys.argv[0]).name, *args]) + '\\n')
key = 'CODEX_HOME' if pathlib.Path(sys.argv[0]).name == 'codex' else 'CLAUDE_CONFIG_DIR'
home = pathlib.Path(os.environ[key])
if args[:3] == ['plugin', 'marketplace', 'add']:
    (home / 'source').write_text(args[3])
elif args[:2] == ['plugin', 'add'] or args[:2] == ['plugin', 'install']:
    if os.environ.get('STUB_SETUP_FAIL'):
        sys.exit(7)
    shutil.copytree(pathlib.Path((home / 'source').read_text()), home / 'plugins/cache/lab/version')
    if os.environ.get('STUB_MISMATCH'):
        (home / 'plugins/cache/lab/version/skills/lab-hpc/SKILL.md').write_text('wrong')
else:
    if os.environ.get('STUB_EMPTY'):
        print(json.dumps({'type': 'item.completed', 'item': {'type': 'command_execution', 'aggregated_output': 'login node'}}))
    else:
        print(json.dumps({'type': 'item.completed', 'item': {'type': 'agent_message', 'text': 'login node'}}))
    if not os.environ.get('STUB_TRUNCATED'):
        print(json.dumps({'type': 'turn.completed'}))
    sys.exit(int(os.environ.get('STUB_RUN_EXIT', '0')))
"""
    for name in ("codex", "claude", "kimi"):
        stub = bindir / name
        stub.write_text(script)
        stub.chmod(0o755)
    regular = tmp_path / "regular-homes"
    regular.mkdir()
    for name in ("codex", "claude", "home"):
        (regular / name).mkdir()
        (regular / name / "sentinel").write_text("preserve me")
    env = {
        **os.environ,
        "HOME": str(regular / "home"),
        "CODEX_HOME": str(regular / "codex"),
        "CLAUDE_CONFIG_DIR": str(regular / "claude"),
        "PATH": f"{bindir}:{os.environ['PATH']}",
        "STUB_CALLS": str(calls),
        "TMPDIR": str(tmp_path),
    }
    return env, calls


def execute(
    env: dict[str, str], agent: str = "codex", case: str = "explicit"
) -> subprocess.CompletedProcess[str]:
    """Run the public command with a selected agent and one case."""
    return subprocess.run(
        ["bash", "tests/eval.sh", "--agent", agent, "--only", case],
        cwd=REPO,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )


def test_codex_setup_and_eval_use_only_codex(tmp_path: Path) -> None:
    """The verified Codex path never invokes another agent or uses the regular home."""
    import json

    env, calls = stub_agent(tmp_path)
    result = execute(env)
    assert result.returncode == 0, result.stdout + result.stderr
    invocations = [json.loads(line) for line in calls.read_text().splitlines()]
    assert len(invocations) == 3
    assert all(call[0] == "codex" for call in invocations)
    assert "read-only" in invocations[-1]
    evidence = json.loads(next(tmp_path.glob("lab-agent-eval-*/evidence.json")).read_text())
    assert evidence["agent"] == "codex"
    assert evidence["content_verified"] is True
    assert evidence["assertions"] == "pass"
    assert evidence["content_sha256"]
    assert evidence["transcripts"]


def test_failed_setup_launches_no_eval(tmp_path: Path) -> None:
    """A failed installation stops before the paid command."""
    env, calls = stub_agent(tmp_path)
    env["STUB_SETUP_FAIL"] = "1"
    result = execute(env)
    assert result.returncode == 1
    assert "setup failed" in result.stderr
    assert len(calls.read_text().splitlines()) == 2


def test_content_mismatch_launches_no_eval(tmp_path: Path) -> None:
    """An installed plugin with different bytes is rejected before launch."""
    env, calls = stub_agent(tmp_path)
    env["STUB_MISMATCH"] = "1"
    result = execute(env)
    assert result.returncode == 1
    assert "content verification failed" in result.stderr
    assert len(calls.read_text().splitlines()) == 2


def test_runner_failure_cannot_pass_matching_output(tmp_path: Path) -> None:
    """Matching final output cannot hide a nonzero runner status."""
    env, _ = stub_agent(tmp_path)
    env["STUB_RUN_EXIT"] = "17"
    result = execute(env)
    assert result.returncode == 1
    assert "runner exited 17" in result.stdout
    assert "EVAL PASS" not in result.stdout


def test_missing_final_answer_cannot_pass_command_output(tmp_path: Path) -> None:
    """A tool's matching output is not the agent's final answer."""
    env, _ = stub_agent(tmp_path)
    env["STUB_EMPTY"] = "1"
    result = execute(env)
    assert result.returncode == 1
    assert "no final answer" in result.stdout


def test_unsupported_codex_case_has_no_setup(tmp_path: Path) -> None:
    """An unsupported case fails before changing an installation."""
    env, calls = stub_agent(tmp_path)
    result = execute(env, case="unslop-zh-original")
    assert result.returncode == 2
    assert "unsupported Codex case" in result.stderr
    assert not calls.exists()


def test_claude_is_explicit_and_isolated(tmp_path: Path) -> None:
    """An explicitly selected Claude run uses only its private installation."""
    import json

    env, calls = stub_agent(tmp_path)
    result = execute(env, agent="claude")
    assert result.returncode == 0, result.stdout + result.stderr
    invocations = [json.loads(line) for line in calls.read_text().splitlines()]
    assert all(call[0] == "claude" for call in invocations)
    assert "stream-json" in invocations[-1]
    context = json.loads(next(tmp_path.glob("lab-agent-eval-*/context.json")).read_text())
    assert list(context["env"]) == ["CLAUDE_CONFIG_DIR"]
    assert str(tmp_path) in context["env"]["CLAUDE_CONFIG_DIR"]
    for name in ("codex", "claude", "home"):
        regular = tmp_path / "regular-homes" / name
        assert sorted(path.name for path in regular.iterdir()) == ["sentinel"]
        assert (regular / "sentinel").read_text() == "preserve me"


def test_progress_without_turn_completion_fails(tmp_path: Path) -> None:
    """Matching progress output cannot substitute for a completed Codex turn."""
    env, _ = stub_agent(tmp_path)
    env["STUB_TRUNCATED"] = "1"
    result = execute(env)
    assert result.returncode == 1
    assert "no final answer" in result.stdout


def test_empty_case_never_becomes_a_full_suite(tmp_path: Path) -> None:
    """An empty --only argument launches neither installation nor the full paid suite."""
    env, calls = stub_agent(tmp_path)
    for agent in ("codex", "claude"):
        result = execute(env, agent=agent, case="")
        assert result.returncode == 2
        assert "unsupported case" in result.stderr
        assert not calls.exists()
