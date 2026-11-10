"""Exercise eval selection and failed runner handling without paid sessions."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
# Everything a run of one case reads: the entry point, the runner, the catalogue and its two
# helpers, the plugin manifest the evidence quotes, and one skill for the mismatch test to
# change in the installed copy.
RUN_FILES = (
    "tests/eval.sh",
    "tests/eval_runner.py",
    "tests/eval_cases.sh",
    "tests/eval_assert.sh",
    "tests/eval_stream.py",
    ".claude-plugin/plugin.json",
    "skills/lab-hpc/SKILL.md",
)


@pytest.fixture(scope="module")
def tree(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Copy the files a run reads into a small git repo, and run the runner from there.

    The runner snapshots, installs and hashes the whole tree it sits in. That is the
    behaviour under test, and its cost grows with the tree: in this repo it was most of
    each test's time. The copy is this checkout's own runner, unchanged, in a
    tree of seven files, so the same snapshot, content check and isolation are proved on a
    tree small enough to hash at once. Nothing in the runner knows it is under test.
    """
    root = tmp_path_factory.mktemp("eval-tree")
    for name in RUN_FILES:
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / name, target)
    git = {
        **os.environ,
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_AUTHOR_NAME": "A Test",
        "GIT_AUTHOR_EMAIL": "test@example.invalid",
        "GIT_COMMITTER_NAME": "A Test",
        "GIT_COMMITTER_EMAIL": "test@example.invalid",
    }
    for command in (["init", "-q"], ["add", "-A"], ["commit", "-q", "-m", "the files a run reads"]):
        subprocess.run(["git", *command], cwd=root, env=git, check=True, capture_output=True)
    return root


LOGIN_VARIABLES = ("CLAUDE_CODE_OAUTH_TOKEN", "ANTHROPIC_API_KEY")
STAND_IN = "stand-in-not-a-credential"


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
with open(os.environ['STUB_CALLS'] + '.login', 'a') as f:
    f.write(('linked' if (home / '.credentials.json').is_symlink() else 'absent') + '\\n')
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
    # A login in the developer's own shell must not decide a test.
    for name in LOGIN_VARIABLES:
        env.pop(name, None)
    return env, calls


def execute(
    tree: Path, env: dict[str, str], agent: str = "codex", case: str = "explicit"
) -> subprocess.CompletedProcess[str]:
    """Run the public command in the small tree, with a selected agent and one case."""
    return subprocess.run(
        ["bash", "tests/eval.sh", "--agent", agent, "--only", case],
        cwd=tree,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )


def test_codex_setup_and_eval_use_only_codex(tmp_path: Path, tree: Path) -> None:
    """The verified Codex path never invokes another agent or uses the regular home."""
    import json

    env, calls = stub_agent(tmp_path)
    result = execute(tree, env)
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


def test_failed_setup_launches_no_eval(tmp_path: Path, tree: Path) -> None:
    """A failed installation stops before the paid command."""
    env, calls = stub_agent(tmp_path)
    env["STUB_SETUP_FAIL"] = "1"
    result = execute(tree, env)
    assert result.returncode == 1
    assert "setup failed" in result.stderr
    assert len(calls.read_text().splitlines()) == 2


def test_content_mismatch_launches_no_eval(tmp_path: Path, tree: Path) -> None:
    """An installed plugin with different bytes is rejected before launch."""
    env, calls = stub_agent(tmp_path)
    env["STUB_MISMATCH"] = "1"
    result = execute(tree, env)
    assert result.returncode == 1
    assert "content verification failed" in result.stderr
    assert len(calls.read_text().splitlines()) == 2


def test_runner_failure_cannot_pass_matching_output(tmp_path: Path, tree: Path) -> None:
    """Matching final output cannot hide a nonzero runner status."""
    env, _ = stub_agent(tmp_path)
    env["STUB_RUN_EXIT"] = "17"
    result = execute(tree, env)
    assert result.returncode == 1
    assert "runner exited 17" in result.stdout
    assert "EVAL PASS" not in result.stdout


def test_missing_final_answer_cannot_pass_command_output(tmp_path: Path, tree: Path) -> None:
    """A tool's matching output is not the agent's final answer."""
    env, _ = stub_agent(tmp_path)
    env["STUB_EMPTY"] = "1"
    result = execute(tree, env)
    assert result.returncode == 1
    assert "no final answer" in result.stdout


def test_unsupported_codex_case_has_no_setup(tmp_path: Path, tree: Path) -> None:
    """An unsupported case fails before changing an installation."""
    env, calls = stub_agent(tmp_path)
    result = execute(tree, env, case="unslop-zh-original")
    assert result.returncode == 2
    assert "unsupported Codex case" in result.stderr
    assert not calls.exists()


def test_claude_is_explicit_and_isolated(tmp_path: Path, tree: Path) -> None:
    """An explicitly selected Claude run uses only its private installation."""
    import json

    env, calls = stub_agent(tmp_path)
    env["CLAUDE_CODE_OAUTH_TOKEN"] = STAND_IN
    result = execute(tree, env, agent="claude")
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


def login_file(tmp_path: Path, text: str) -> None:
    """Write a made-up login file into the stand-in Claude config folder."""
    (tmp_path / "regular-homes" / "claude" / ".credentials.json").write_text(text)


def oauth_login(expires_in_seconds: float) -> str:
    """Build a made-up login whose expiry is relative to now, in milliseconds."""
    import json
    import time

    expiry = int((time.time() + expires_in_seconds) * 1000)
    return json.dumps({"claudeAiOauth": {"accessToken": STAND_IN, "expiresAt": expiry}})


def assert_no_login_refusal(tmp_path: Path, result: subprocess.CompletedProcess[str]) -> None:
    """Check that a refusal names the cause and the remedy, is recorded and reveals no login."""
    import json

    assert result.returncode == 1
    assert "no usable Claude login" in result.stderr
    assert "claude setup-token" in result.stderr
    assert "CLAUDE_CODE_OAUTH_TOKEN" in result.stderr
    evidence_path = next(tmp_path.glob("lab-agent-eval-*/evidence.json"))
    evidence = json.loads(evidence_path.read_text())
    assert evidence["stage"] == "setup"
    assert "no usable Claude login" in evidence["error"]
    assert STAND_IN not in result.stdout + result.stderr + evidence_path.read_text()


def test_expired_claude_login_launches_nothing(tmp_path: Path, tree: Path) -> None:
    """An expired login file with no login in the environment stops setup."""
    env, calls = stub_agent(tmp_path)
    env["LAB_EVAL_PLATFORM"] = "darwin"
    login_file(tmp_path, oauth_login(-3600))
    result = execute(tree, env, agent="claude")
    assert_no_login_refusal(tmp_path, result)
    assert "expired" in result.stderr
    assert "Keychain" in result.stderr
    assert not calls.exists()


def test_expired_claude_login_off_macos_is_linked_as_before(tmp_path: Path, tree: Path) -> None:
    """Off macOS the login file is the live store, so an old expiry does not stop the run."""
    env, calls = stub_agent(tmp_path)
    env["LAB_EVAL_PLATFORM"] = "linux"
    login_file(tmp_path, oauth_login(-3600))
    result = execute(tree, env, agent="claude")
    assert result.returncode == 0, result.stdout + result.stderr
    assert Path(f"{calls}.login").read_text().split() == ["linked"] * 3


def test_unparsable_claude_login_launches_nothing(tmp_path: Path, tree: Path) -> None:
    """A login file that is not a login, with no login in the environment, stops setup."""
    for platform in ("darwin", "linux"):
        root = tmp_path / platform
        root.mkdir()
        env, calls = stub_agent(root)
        env["LAB_EVAL_PLATFORM"] = platform
        login_file(root, STAND_IN)
        result = execute(tree, env, agent="claude")
        assert_no_login_refusal(root, result)
        assert not calls.exists()


def test_missing_claude_login_launches_nothing(tmp_path: Path, tree: Path) -> None:
    """No login file and no login in the environment stops setup, on every platform."""
    for platform in ("darwin", "linux"):
        root = tmp_path / platform
        root.mkdir()
        env, calls = stub_agent(root)
        env["LAB_EVAL_PLATFORM"] = platform
        result = execute(tree, env, agent="claude")
        assert_no_login_refusal(root, result)
        assert ("Keychain" in result.stderr) == (platform == "darwin")
        assert not calls.exists()


def test_environment_login_runs_without_linking_a_stale_file(tmp_path: Path, tree: Path) -> None:
    """A login in the environment runs the case, and the agent never sees the expired file."""
    for number, name in enumerate(LOGIN_VARIABLES):
        root = tmp_path / str(number)
        root.mkdir()
        env, calls = stub_agent(root)
        env[name] = STAND_IN
        env["LAB_EVAL_PLATFORM"] = "darwin"
        login_file(root, oauth_login(-3600))
        result = execute(tree, env, agent="claude")
        assert result.returncode == 0, result.stdout + result.stderr
        assert "EVAL PASS" in result.stdout
        seen = Path(f"{calls}.login").read_text().split()
        assert seen == ["absent"] * 3
        assert STAND_IN not in next(root.glob("lab-agent-eval-*/evidence.json")).read_text()


def test_fresh_claude_login_is_linked_for_the_run_only(tmp_path: Path, tree: Path) -> None:
    """A login file that has not expired reaches the agent as a link, removed afterwards."""
    env, calls = stub_agent(tmp_path)
    env["LAB_EVAL_PLATFORM"] = "darwin"
    login_file(tmp_path, oauth_login(3600))
    result = execute(tree, env, agent="claude")
    assert result.returncode == 0, result.stdout + result.stderr
    assert Path(f"{calls}.login").read_text().split() == ["linked"] * 3
    home = next(tmp_path.glob("lab-agent-eval-*/agent-home"))
    assert not (home / ".credentials.json").exists()
    assert (tmp_path / "regular-homes/claude/.credentials.json").is_file()


def test_progress_without_turn_completion_fails(tmp_path: Path, tree: Path) -> None:
    """Matching progress output cannot substitute for a completed Codex turn."""
    env, _ = stub_agent(tmp_path)
    env["STUB_TRUNCATED"] = "1"
    result = execute(tree, env)
    assert result.returncode == 1
    assert "no final answer" in result.stdout


def test_empty_case_never_becomes_a_full_suite(tmp_path: Path, tree: Path) -> None:
    """An empty --only argument launches neither installation nor the full paid suite."""
    env, calls = stub_agent(tmp_path)
    for agent in ("codex", "claude"):
        result = execute(tree, env, agent=agent, case="")
        assert result.returncode == 2
        assert "unsupported case" in result.stderr
        assert not calls.exists()
