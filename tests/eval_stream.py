"""Read final answers and Skill calls from Claude stream-json transcripts."""

from __future__ import annotations

import json
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any


def events(path: Path) -> Iterator[dict[str, Any]]:
    """Yield JSON objects and ignore non-JSON lines."""
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(event, dict):
                yield event


def write_answer(path: Path) -> bool:
    """Print the last result answer and report whether one exists."""
    answers = [
        result
        for event in events(path)
        if event.get("type") == "result" and isinstance((result := event.get("result")), str)
    ]
    if not answers:
        return False
    sys.stdout.write(answers[-1])
    if not answers[-1].endswith("\n"):
        sys.stdout.write("\n")
    return True


def has_skill_call(path: Path, target: str) -> bool:
    """Report whether an assistant event invokes the named Skill."""
    target = target.rsplit(":", 1)[-1]
    for event in events(path):
        if event.get("type") != "assistant":
            continue
        message = event.get("message")
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") != "tool_use" or block.get("name") != "Skill":
                continue
            inputs = block.get("input")
            if not isinstance(inputs, dict):
                continue
            skill = inputs.get("skill")
            if isinstance(skill, str) and skill.rsplit(":", 1)[-1] == target:
                return True
    return False


def main() -> int:
    """Run the answer or skill command."""
    args = sys.argv[1:]
    if len(args) == 2 and args[0] == "answer":
        return 0 if write_answer(Path(args[1])) else 1
    if len(args) == 3 and args[0] == "skill":
        return 0 if has_skill_call(Path(args[1]), args[2]) else 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
