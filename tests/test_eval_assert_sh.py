"""The shared shell helper owns eval regex and Skill assertion semantics."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
HELPER = REPO / "tests" / "eval_assert.sh"
FIXTURES = REPO / "tests" / "fixtures" / "eval"
SKILL = "lab-unslop-chinese-kimi"


def run_assert(*args: object) -> tuple[int, str]:
    """Run the shared helper with arguments and return its status and output."""
    result = subprocess.run(
        ["bash", "-c", 'source "$1"; shift; "$@"', "_", str(HELPER), *map(str, args)],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    return result.returncode, result.stdout + result.stderr


@pytest.mark.parametrize(("sensitive", "expected"), [("false", 0), ("true", 1)])
def test_eval_grep_honors_case_sensitivity(sensitive: str, expected: int) -> None:
    """Case-insensitive matching is the default; true enables exact case."""
    fixture = FIXTURES / "unslop-chinese-kimi-mixed.fail-also-case.txt"
    rc, output = run_assert("eval_grep", sensitive, "^RUN: API_TOKEN", fixture)
    assert rc == expected, output


def test_eval_grep_keeps_case_sensitive_matches() -> None:
    """A matching protected line passes with case sensitivity enabled."""
    fixture = FIXTURES / "unslop-chinese-kimi-mixed.pass.txt"
    rc, output = run_assert("eval_grep", "true", "^RUN: API_TOKEN", fixture)
    assert (rc, output) == (0, "")


def test_required_skill_passes_with_an_actual_invocation() -> None:
    """A required Skill succeeds when its actual tool call is present."""
    fixture = FIXTURES / "unslop-chinese-kimi-original.pass.txt"
    rc, output = run_assert("eval_skill_assert", SKILL, fixture)
    assert (rc, output) == (0, "")


def test_required_skill_reports_a_missing_invocation() -> None:
    """A required Skill fails with a useful reason when its call is absent."""
    fixture = FIXTURES / "unslop-chinese-kimi-original.fail-skill.txt"
    rc, output = run_assert("eval_skill_assert", SKILL, fixture)
    assert rc == 1
    assert output == f"no Skill invocation for {SKILL}\n"


def test_forbidden_skill_passes_without_an_invocation() -> None:
    """A forbidden Skill succeeds when its call is absent."""
    fixture = FIXTURES / "unslop-chinese-kimi-not-chinese.pass.txt"
    rc, output = run_assert("eval_skill_assert", f"!{SKILL}", fixture)
    assert (rc, output) == (0, "")


def test_forbidden_skill_reports_an_invocation() -> None:
    """A forbidden Skill fails with its name after ! is stripped."""
    fixture = FIXTURES / "unslop-chinese-kimi-not-chinese.fail-skill.txt"
    rc, output = run_assert("eval_skill_assert", f"!{SKILL}", fixture)
    assert rc == 1
    assert output == f"invoked forbidden Skill {SKILL}\n"
