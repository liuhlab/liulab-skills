"""The summary of what is new upstream: forked originals, the pstack section and eval reruns.

A forked skill and everything taken from pstack change only by hand, so the sync says what
upstream did to their originals and leaves the porting to the maintainer. pstack's pin moves
forward in the same run, so one pull request covers both upstreams.
"""

from __future__ import annotations

from pathlib import Path

from tests.upstream_sync.conftest import (
    PIN,
    MakeLab,
    Upstream,
    follow_by_review,
    numbered,
    skill,
)


def test_a_change_to_a_forked_skills_original_is_listed_for_porting(
    upstream: Upstream, make_lab: MakeLab
) -> None:
    """The files and commits upstream changed are named; an untouched original says so."""
    upstream.add("grilling", bucket="productivity")
    upstream.add("teach", bucket="productivity")
    upstream.add("retro", bucket="productivity")
    base = upstream.commit()
    lab = make_lab(
        upstream,
        base,
        tracked={"grilling": "productivity"},
        forked={"teach": "productivity", "retro": "productivity"},
    )
    upstream.write("skills/productivity/teach/SKILL.md", skill("teach", ["Teach by example."]))
    upstream.write("skills/productivity/teach/extra.md", "# Extra\n")
    tip = upstream.commit("teach: explain by example")

    run = lab.merge(upstream)

    assert run.returncode == 0, run.stdout + run.stderr
    assert (
        f"- `skills/teach`, from `teach`: upstream changed `SKILL.md`, `extra.md` in 1 commit(s): "
        f"`{tip[:7]}` teach: explain by example. Port by hand what is worth taking.\n"
    ) in run.stdout
    assert "- `skills/retro`, from `retro`: unchanged upstream.\n" in run.stdout


def test_the_pstack_section_has_a_line_per_mapped_item_and_per_new_skill(
    upstream: Upstream, make_lab: MakeLab, env: dict[str, str], tmp_path: Path
) -> None:
    """Token cuts are low priority, a file item is not counted in its directory, the pin moves."""
    upstream.add("grilling", bucket="productivity")
    lab = make_lab(upstream, upstream.commit(), tracked={"grilling": "productivity"})
    pstack = Upstream(tmp_path / "pstack", env)
    for name in ("unslop", "ketchup", "poteto-mode", "how"):
        pstack.write(f"pstack/skills/{name}/SKILL.md", skill(name))
    pstack.write("pstack/skills/poteto-mode/playbooks/hillclimb.md", "# Hillclimb\n\nClimb.\n")
    base = pstack.commit("pstack 0.15.17")
    follow_by_review(
        lab,
        "pstack",
        base,
        {
            "how": "skills/hq-mode/references/playbooks/investigation.md",
            "ketchup": "skills/ketchup",
            "poteto-mode": "skills/hq-mode/SKILL.md",
            "poteto-mode/playbooks/hillclimb.md": "skills/hq-mode/references/playbooks/hill.md",
            "unslop": "skills/unslop",
        },
    )
    lines = numbered("unslop")
    pstack.write("pstack/skills/unslop/SKILL.md", skill("unslop", ["Step 1, shorter.", *lines[1:]]))
    mode = numbered("poteto-mode")
    pstack.write(
        "pstack/skills/poteto-mode/SKILL.md", skill("poteto-mode", ["Shorter.", *mode[1:]])
    )
    cut = pstack.commit("refactor(pstack): distill skill prompts to cut tokens (#538)")
    pstack.write(
        "pstack/skills/unslop/SKILL.md",
        skill("unslop", ["Step 1, shorter.", "Keep terms of art.", *lines[2:]]),
    )
    keep = pstack.commit("feat(pstack): unslop keeps terms of art")
    pstack.write(
        "pstack/skills/poteto-mode/playbooks/hillclimb.md", "# Hillclimb\n\nMetric first.\n"
    )
    climb = pstack.commit("docs(pstack): hillclimb names the metric first")
    pstack.write("pstack/skills/correct/SKILL.md", skill("correct"))
    pstack.remove("pstack/skills/how")
    tip = pstack.commit("feat(pstack): add /correct, fold how into why")

    run = lab.merge(upstream, pstack=pstack)

    assert run.returncode == 0, run.stdout + run.stderr
    assert (
        f"## pstack: `{base[:7]}` to `{tip[:7]}`\n\n### Mapped items\n\n"
        "- `how`, feeding `skills/hq-mode/references/playbooks/investigation.md`: gone from "
        "upstream's tip, deleted or moved.\n"
        "- `ketchup`, feeding `skills/ketchup`: unchanged.\n"
        "- `poteto-mode`, feeding `skills/hq-mode/SKILL.md`: +1 -1 lines in 1 commit(s): "
        f"`{cut[:7]}` refactor(pstack): distill skill prompts to cut tokens (#538). "
        "Low priority: model and token cuts only.\n"
        "- `poteto-mode/playbooks/hillclimb.md`, feeding "
        "`skills/hq-mode/references/playbooks/hill.md`: +1 -1 lines in 1 commit(s): "
        f"`{climb[:7]}` docs(pstack): hillclimb names the metric first.\n"
        "- `unslop`, feeding `skills/unslop`: +2 -2 lines in 2 commit(s): "
        f"`{keep[:7]}` feat(pstack): unslop keeps terms of art; "
        f"`{cut[:7]}` refactor(pstack): distill skill prompts to cut tokens (#538).\n\n"
        "### New skills\n\n"
        "- `correct`: new in pstack at `pstack/skills/correct`. Take it as an idea, or leave it.\n"
    ) in run.stdout
    assert lab.json("upstream/pstack/pin.json")["commit"] == tip
    assert f"`upstream/pstack/pin.json` moved from `{base[:7]}` to `{tip[:7]}`" in run.stdout
    assert lab.json(PIN)["commit"] == upstream.git("rev-parse", "HEAD")


def test_a_reviewed_upstream_without_a_clone_is_refused(
    upstream: Upstream, make_lab: MakeLab, env: dict[str, str], tmp_path: Path
) -> None:
    """Both pins move in one pull request, so a merge needs every upstream's clone."""
    upstream.add("grilling", bucket="productivity")
    lab = make_lab(upstream, upstream.commit(), tracked={"grilling": "productivity"})
    pstack = Upstream(tmp_path / "pstack", env)
    pstack.write("pstack/skills/unslop/SKILL.md", skill("unslop"))
    follow_by_review(lab, "pstack", pstack.commit(), {"unslop": "skills/unslop"})

    run = lab.merge(upstream)

    assert run.returncode == 2
    assert "--clone pstack=<dir>" in run.stderr
    assert lab.git("status", "--porcelain") == ""


def test_an_eval_case_is_listed_only_for_a_skill_upstream_changed(
    upstream: Upstream, make_lab: MakeLab
) -> None:
    """A case named `<skill>-*` is listed when upstream touched that skill, with a word to ask."""
    upstream.add("prototype")
    upstream.add("diagnosing-bugs")
    base = upstream.commit()
    lab = make_lab(
        upstream, base, tracked={"prototype": "engineering", "diagnosing-bugs": "engineering"}
    )
    repo = Path(__file__).resolve().parents[2]
    for name in ("eval.sh", "eval_cases.sh"):
        lab.write(f"tests/{name}", (repo / "tests" / name).read_text())
    lines = numbered("diagnosing-bugs")
    lab.write("skills/diagnosing-bugs/SKILL.md", skill("diagnosing-bugs", [*lines, "Slow loop."]))
    lab.commit("eval cases, and a lab edit upstream never touched")
    upstream.write("skills/engineering/prototype/SKILL.md", skill("prototype", ["Reworded."]))
    upstream.commit()

    run = lab.merge(upstream)

    assert run.returncode == 0, run.stdout + run.stderr
    assert (
        "### Eval cases to rerun\n\n- `prototype-language`: upstream changed `prototype`. "
        "A case costs tokens: ask before running it.\n\n"
    ) in run.stdout
    assert "diagnosing-bugs-slow-loop" not in run.stdout


def test_an_eval_case_belongs_to_the_longest_skill_name_it_starts_with(
    upstream: Upstream, make_lab: MakeLab
) -> None:
    """`implement-spec-plan` guards `implement-spec`, so a change to `implement` leaves it out."""
    upstream.add("implement")
    upstream.add("implement-spec")
    base = upstream.commit()
    lab = make_lab(
        upstream, base, tracked={"implement": "engineering", "implement-spec": "engineering"}
    )
    lab.write("tests/eval_cases.sh", 'CASES="implement-lanes implement-spec-plan"\n')
    lab.commit("eval cases")
    upstream.write("skills/engineering/implement/SKILL.md", skill("implement", ["Reworded."]))
    upstream.commit()

    run = lab.merge(upstream)

    assert run.returncode == 0, run.stdout + run.stderr
    assert "- `implement-lanes`: upstream changed `implement`." in run.stdout
    assert "implement-spec-plan" not in run.stdout
