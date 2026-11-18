"""`stale-worktrees.sh` removes only a worktree that holds no work, and reports the rest.

Each test builds a folder of clones like `~/src`: a bare `origin` and one clone of it, with
worktrees in the states an agent leaves behind. The sweep spares anything touched within a
day, so `age` sets a worktree's or a folder's times two days back. A stand-in `gh` first on
PATH answers how many merged pull requests hold a branch's commit, so no test reaches GitHub.
"""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import time
from pathlib import Path

import pytest

from tests.conftest import program

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "skills" / "hq-mode" / "scripts" / "stale-worktrees.sh"

# Each sweep reads every process's working folder through lsof, which is heavy on the kernel.
# One worker runs them all, so no two of these tests' lsof calls compete.
pytestmark = pytest.mark.xdist_group("stale-worktrees")

GH = '#!/bin/sh\nprintf "%s\\n" "${STUB_GH_MERGED:-0}"\n'


def git_env(home: Path, stubs: Path | None = None) -> dict[str, str]:
    """Return an environment where git reads no config, with `stubs` first on PATH."""
    run = subprocess.run(["git", "--exec-path"], capture_output=True, text=True, check=True)
    own = Path(run.stdout.strip())
    path = os.environ["PATH"]
    if os.access(own / "git", os.X_OK):  # skip the Xcode launcher on a Mac
        path = f"{own}{os.pathsep}{path}"
    if stubs:
        path = f"{stubs}{os.pathsep}{path}"
    clean = {k: v for k, v in os.environ.items() if not k.startswith(("GIT_", "STUB_"))}
    clean.update(
        PATH=path,
        HOME=str(home),
        GIT_CONFIG_NOSYSTEM="1",
        GIT_AUTHOR_NAME="Fixture",
        GIT_AUTHOR_EMAIL="fixture@example.invalid",
        GIT_COMMITTER_NAME="Fixture",
        GIT_COMMITTER_EMAIL="fixture@example.invalid",
    )
    return clean


@pytest.fixture
def env(tmp_path: Path) -> dict[str, str]:
    """Return an environment with git reading no config and the stand-in `gh` first on PATH."""
    stubs = tmp_path / "bin"
    stubs.mkdir()
    program(stubs, "gh", GH)
    return git_env(tmp_path, stubs)


@pytest.fixture(scope="session")
def template(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Build a bare `origin` with one commit and `src/repo`, its clone, once per run."""
    root = tmp_path_factory.mktemp("stale-worktrees")
    env = git_env(root)
    origin, repo = root / "origin.git", root / "src" / "repo"
    git(env, root, "init", "-q", "--bare", "-b", "main", "--template=", str(origin))
    git(env, root, "clone", "-q", "--template=", str(origin), str(repo))
    git(env, repo, "symbolic-ref", "HEAD", "refs/heads/main")  # an empty clone has no branch
    commit(env, repo, "first")
    git(env, repo, "push", "-q", "origin", "main")
    git(env, repo, "remote", "set-head", "origin", "main")
    return root


@pytest.fixture
def src(tmp_path: Path, env: dict[str, str], template: Path) -> Path:
    """Return a folder of clones holding `repo`, a copy of the template's clone and origin."""
    shutil.copytree(template / "origin.git", tmp_path / "origin.git", symlinks=True)
    shutil.copytree(template / "src", tmp_path / "src", symlinks=True)
    repo = tmp_path / "src" / "repo"
    git(env, repo, "remote", "set-url", "origin", str(tmp_path / "origin.git"))
    return (tmp_path / "src").resolve()


def git(env: dict[str, str], where: Path, *args: str) -> str:
    """Run git in `where` and return what it prints."""
    run = subprocess.run(
        ["git", "-C", str(where), *args], env=env, capture_output=True, text=True, check=True
    )
    return run.stdout


def commit(env: dict[str, str], where: Path, name: str) -> None:
    """Commit a new file named `name` in `where`."""
    (where / name).write_text(name)
    git(env, where, "add", name)
    git(env, where, "commit", "-q", "-m", name)


def worktree(env: dict[str, str], src: Path, name: str, branch: str | None = None) -> Path:
    """Add a worktree of `repo` at `src/<name>` on origin/main, on `branch` or detached."""
    path = src / name
    start = ["-b", branch] if branch else ["--detach"]
    git(env, src / "repo", "worktree", "add", "-q", *start, str(path), "origin/main")
    return path


def age(*paths: Path) -> None:
    """Set each worktree's last checkout and commit, or each folder's time, two days back."""
    old = time.time() - 2 * 86400
    for path in paths:
        dot_git = path / ".git"
        if not dot_git.is_file():
            os.utime(path, (old, old))
            continue
        admin = Path(dot_git.read_text().split(maxsplit=1)[1].strip())
        for kept in (admin / "HEAD", admin / "logs" / "HEAD"):
            if kept.exists():
                os.utime(kept, (old, old))


def sweep(env: dict[str, str], *args: str, cwd: Path) -> list[list[str]]:
    """Run the script and return its lines split at tabs."""
    run = subprocess.run(
        ["bash", str(SCRIPT), *args], env=env, cwd=cwd, capture_output=True, text=True
    )
    assert run.returncode == 0, run.stderr
    return [line.split("\t") for line in run.stdout.splitlines()]


def test_it_reports_landed_worktrees_and_empty_folders(src, env):
    """Without --remove it only reports: a landed worktree, unlanded work, an empty folder."""
    landed = worktree(env, src, "repo-1", "work/1")
    detached = worktree(env, src, "repo-2-triage")
    ahead = worktree(env, src, "repo-3", "work/3")
    commit(env, ahead, "unlanded")
    (src / "repo-wt").mkdir()
    age(landed, detached, ahead, src / "repo-wt")

    found = sweep(env, cwd=src / "repo")  # no folder given: the one holding this clone

    assert ["stale", str(landed), "its commit is in origin/main"] in found
    assert ["stale", str(detached), "its commit is in origin/main"] in found
    assert ["keep", str(ahead), "it has commits not in origin/main"] in found
    assert ["empty", str(src / "repo-wt")] in found
    assert landed.exists()
    assert "work/1" in git(env, src / "repo", "branch")


def test_remove_keeps_a_worktree_with_files_a_lock_or_a_checkout_within_a_day(src, env):
    """A worktree with an untracked file, a lock, or a checkout under a day old stays."""
    dirty = worktree(env, src, "repo-1", "work/1")
    (dirty / "notes.md").write_text("draft")
    locked = worktree(env, src, "repo-2", "work/2")
    git(env, src / "repo", "worktree", "lock", "--reason", "agent busy", str(locked))
    age(dirty, locked)
    fresh = worktree(env, src, "repo-3", "work/3")  # a peer's, before its first edit
    (src / "repo-new").mkdir()

    found = sweep(env, "--remove", str(src), cwd=src)

    assert ["keep", str(dirty), "uncommitted or untracked files"] in found
    assert ["keep", str(locked), "locked: agent busy"] in found
    assert ["keep", str(fresh), "checked out or committed to within a day"] in found
    assert dirty.exists()
    assert locked.exists()
    assert fresh.exists()
    assert (src / "repo-new").exists()


def test_remove_deletes_only_landed_worktrees_their_branches_and_empty_folders(src, env):
    """--remove takes landed worktrees, a branch and the empty folder, nothing else."""
    landed = worktree(env, src, "repo-1", "work/1")
    detached = worktree(env, src, "repo-2-triage")  # no branch to delete
    ahead = worktree(env, src, "repo-3", "work/3")
    commit(env, ahead, "unlanded")
    (src / "repo-wt").mkdir()
    age(landed, detached, ahead, src / "repo-wt")

    found = sweep(env, "--remove", str(src), cwd=src)

    assert ["removed", str(landed), "its commit is in origin/main"] in found
    assert ["removed", str(detached), "its commit is in origin/main"] in found
    assert ["rmdir", str(src / "repo-wt")] in found
    assert not landed.exists()
    assert not detached.exists()
    assert not (src / "repo-wt").exists()
    assert ahead.exists()
    branches = git(env, src / "repo", "branch")
    assert "work/1" not in branches
    assert "work/3" in branches


def test_a_squash_merged_branch_lands_when_github_merged_that_exact_commit(src, env):
    """A commit not in main lands when GitHub says a merged pull request holds it."""
    squashed = worktree(env, src, "repo-1", "work/1")
    commit(env, squashed, "squashed")
    age(squashed)

    found = sweep({**env, "STUB_GH_MERGED": "1"}, "--remove", str(src), cwd=src)

    assert ["removed", str(squashed), "a merged pull request holds its commit"] in found
    assert "work/1" not in git(env, src / "repo", "branch")


def test_a_worktree_a_process_runs_in_is_kept(src, env):
    """A process working in a landed worktree keeps it."""
    busy = worktree(env, src, "repo-1", "work/1")
    age(busy)
    server = subprocess.Popen(
        ["/bin/sh", "-c", "sleep 30; :", "sh", f"{busy}/"], cwd=busy, start_new_session=True
    )
    try:
        found = sweep(env, "--remove", str(src), cwd=src)
    finally:
        os.killpg(server.pid, signal.SIGKILL)
        server.wait()
    assert ["keep", str(busy), f"process {server.pid} runs in it"] in found
    assert busy.exists()


def test_a_process_running_from_a_deleted_folder_is_reported_and_left_running(src, env):
    """A process whose program sits in a deleted folder is named, and keeps running."""
    # Its program path is argv[0]: macOS kills a copied system binary, so name one instead.
    python = src / "repo" / ".claude" / "worktrees" / "agent-1" / ".pixi" / "bin" / "python"
    server = subprocess.Popen(
        [str(python), "30"], executable=shutil.which("sleep"), start_new_session=True
    )
    try:
        found = sweep(env, "--remove", str(src), cwd=src)
        assert server.poll() is None
    finally:
        server.kill()
        server.wait()
    assert ["orphan", str(server.pid), f"{python} 30"] in found
