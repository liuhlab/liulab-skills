"""`tests/eval.sh` folds a plan file the transcript names back into the transcript.

A plan-mode session may print only a pointer to its plan file, so the assertions have to read
the plan as well. These tests run `eval.sh --only` against a stub `claude` that prints such a
pointer, with HOME set to a fake home holding the plan. No real session starts and nothing
spends a token: the stub is first on PATH, and each test checks it was the one called.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
# Any plan-mode case does; the fold runs before any of its assertions.
CASE = "edison-kosmos"
PLAN_TEXT = "Kosmos is a chat session on a project that fans out into many tasks."


@pytest.mark.parametrize("from_home", [True, False], ids=["tilde", "absolute"])
def test_a_named_plan_file_is_folded_into_the_transcript(tmp_path: Path, from_home: bool) -> None:
    """A plan named as `~/.claude/plans/x.md` or by its full path lands in the transcript."""
    home = tmp_path / "home"
    plan = home / ".claude" / "plans" / "fixture-plan.md"
    plan.parent.mkdir(parents=True)
    plan.write_text(PLAN_TEXT + "\n", encoding="utf-8")
    pointer = "~/.claude/plans/fixture-plan.md" if from_home else str(plan)

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    calls = tmp_path / "claude-calls"
    stub = bin_dir / "claude"
    stub.write_text(
        f"#!/bin/sh\necho x >>'{calls}'\n"
        + "printf '%s\\n' "
        + repr(json.dumps({"type": "result", "result": f"The plan is written to `{pointer}`."}))
        + "\n",
        encoding="utf-8",
    )
    stub.chmod(0o755)

    runs = tmp_path / "runs"
    runs.mkdir()
    env = {
        **os.environ,
        "HOME": str(home),
        "TMPDIR": str(runs),
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
    }
    context = tmp_path / "context.json"
    context.write_text(json.dumps({"agent": "claude", "env": {}, "plugin_root": str(home)}))
    env.update(LAB_EVAL_CONTEXT=str(context), LAB_EVAL_WORKSPACE=str(tmp_path))
    result = subprocess.run(
        ["bash", str(REPO / "tests" / "eval_cases.sh"), "--only", CASE],
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    report = result.stdout + result.stderr

    assert calls.read_text(encoding="utf-8").count("x") == 1, report
    transcripts = list(runs.glob(f"lab-skill-eval.*/{CASE}.txt"))
    assert len(transcripts) == 1, report
    assert result.returncode == 0, report
    assert "EVAL PASS" in report
    transcript = transcripts[0].with_name(f"{CASE}.answer.txt").read_text(encoding="utf-8")
    assert f"--- plan file {plan} ---" in transcript
    assert PLAN_TEXT in transcript
