"""Forking a tracked skill, and the runs the sync refuses before writing anything.

Forking is one recorded step: the skill leaves its pin's name map and gains an attribution
record at the pin's commit, in the shapes `upstream/README.md` gives. A refusal exits 2 and
leaves the lab tree exactly as it was, so a maintainer never has to undo half a sync.
"""

from __future__ import annotations

from tests.upstream_sync.conftest import ATTRIBUTION, PIN, UPSTREAM, MakeLab, Upstream


def test_forking_moves_a_skill_from_the_name_map_to_an_attribution_record(
    upstream: Upstream, make_lab: MakeLab
) -> None:
    """The record takes the pin's commit, and both files keep the README's layout."""
    upstream.add("grilling", bucket="productivity")
    upstream.add("tdd")
    base = upstream.commit()
    lab = make_lab(upstream, base, tracked={"grilling": "productivity", "tdd": "engineering"})

    run = lab.sync("fork", "tdd", "--changes", "Golden fixtures carry the tolerance rule.")

    assert run.returncode == 0, run.stdout + run.stderr
    assert lab.json(PIN)["items"] == {"grilling": "skills/grilling"}
    assert lab.read(ATTRIBUTION) == (
        "{\n"
        '  "skills/tdd": {\n'
        '    "from": [\n'
        f'      {{"upstream": "{UPSTREAM}", "item": "tdd", "commit": "{base}"}}\n'
        "    ],\n"
        '    "changes": "Golden fixtures carry the tolerance rule."\n'
        "  }\n"
        "}\n"
    )
    assert lab.exists("skills/tdd/SKILL.md")


def test_forking_an_untracked_skill_is_refused(upstream: Upstream, make_lab: MakeLab) -> None:
    """Only a skill a merge pin maps can be forked; anything else changes nothing.

    This test runs the script at its command line, as a maintainer does, and the others run it
    in the test's process: here the exit status is the process's own.
    """
    upstream.add("grilling", bucket="productivity")
    base = upstream.commit()
    lab = make_lab(upstream, base, tracked={"grilling": "productivity"})

    run = lab.sync("fork", "lab-hpc", cli=True)

    assert run.returncode == 2
    assert "not a tracked skill" in run.stderr
    assert lab.git("status", "--porcelain") == ""


def test_a_merge_with_uncommitted_changes_is_refused(upstream: Upstream, make_lab: MakeLab) -> None:
    """The sync deletes and rewrites files, so it starts only from a tree git can restore."""
    upstream.add("grilling", bucket="productivity")
    base = upstream.commit()
    lab = make_lab(upstream, base, tracked={"grilling": "productivity"})
    lab.write("skills/grilling/WIP.md", "# Unsaved work\n")
    upstream.write("skills/productivity/grilling/SKILL.md", "---\nname: grilling\n---\n")
    upstream.commit()

    run = lab.merge(upstream)

    assert run.returncode == 2
    assert "uncommitted changes" in run.stderr
    assert lab.git("status", "--porcelain") == "?? skills/grilling/WIP.md"
    assert lab.json(PIN)["commit"] == base


def test_a_merge_with_no_clone_is_refused_and_says_how_to_get_one(
    upstream: Upstream, make_lab: MakeLab
) -> None:
    """A merged upstream needs its clone; the refusal names the command that makes one."""
    upstream.add("grilling", bucket="productivity")
    base = upstream.commit()
    lab = make_lab(upstream, base, tracked={"grilling": "productivity"})

    run = lab.merge()

    assert run.returncode == 2
    assert f"--clone {UPSTREAM}=<dir>" in run.stderr
    assert "git clone https://example.invalid/fixture-skills" in run.stderr
    assert lab.git("status", "--porcelain") == ""
