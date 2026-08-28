"""Tests for smart_update_kimi.sh (Kimi Code CLI update wrapper)."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALL_SCRIPT = REPO_ROOT / "tools" / "install_aris_kimi.sh"
UPDATE_SCRIPT = REPO_ROOT / "tools" / "smart_update_kimi.sh"


def run(
    cmd: list[str], *, cwd: Path | None = None, check: bool = True
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd or REPO_ROOT,
        text=True,
        capture_output=True,
        check=check,
    )


def git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return run(
        ["git", "-C", str(repo), "-c", "user.name=Test", "-c", "user.email=t@example.com", *args]
    )


def make_skill(path: Path, body: str) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "SKILL.md").write_text(body)


def make_git_aris_repo(root: Path, tag: str = "business-research-suite-v0.0.1") -> Path:
    """Minimal skills-kimi repo under git, tagged with the given v0.0.1 tag."""
    repo = root / "aris"
    (repo / "tools").mkdir(parents=True)
    shutil.copy(INSTALL_SCRIPT, repo / "tools" / INSTALL_SCRIPT.name)
    shutil.copy(UPDATE_SCRIPT, repo / "tools" / UPDATE_SCRIPT.name)
    make_skill(repo / "skills" / "skills-kimi" / "alpha", "# kimi alpha v1\n")
    make_skill(repo / "skills" / "skills-kimi" / "beta", "# kimi beta v1\n")
    (repo / "skills" / "skills-kimi" / "shared-references").mkdir(parents=True, exist_ok=True)
    (repo / "skills" / "skills-kimi" / "shared-references" / "reviewer-routing.md").write_text(
        "kimi routing v1\n"
    )
    (repo / "AGENT_GUIDE.md").write_text("# Agent Guide\n")
    git(repo, "init", "--quiet", "--initial-branch=main")
    git(repo, "add", "-A")
    git(repo, "commit", "--quiet", "-m", "v0.0.1")
    git(repo, "tag", tag)
    return repo


def bump_repo(repo: Path, tag: str = "business-research-suite-v0.0.2") -> str:
    """Add a skill, tag the v0.0.2 tag, return to v0.0.1."""
    make_skill(repo / "skills" / "skills-kimi" / "gamma", "# kimi gamma v2\n")
    git(repo, "add", "-A")
    git(repo, "commit", "--quiet", "-m", "v0.0.2")
    git(repo, "tag", tag)
    sha_v2 = git(repo, "rev-parse", "HEAD").stdout.strip()
    git(repo, "checkout", "--quiet", "HEAD~1")
    return sha_v2


def head_sha(repo: Path) -> str:
    return git(repo, "rev-parse", "HEAD").stdout.strip()


def test_smart_update_kimi_dry_run_changes_nothing(tmp_path: Path) -> None:
    repo = make_git_aris_repo(tmp_path)
    sha_v2 = bump_repo(repo)
    sha_before = head_sha(repo)

    result = run(["bash", str(repo / "tools" / "smart_update_kimi.sh")])

    assert result.returncode == 0
    assert "business-research-suite-v0.0.2" in result.stdout
    assert "Dry-run only" in result.stdout
    assert head_sha(repo) == sha_before
    assert head_sha(repo) != sha_v2


def test_smart_update_kimi_apply_updates_clone_and_project(tmp_path: Path) -> None:
    repo = make_git_aris_repo(tmp_path)
    project = tmp_path / "project"
    project.mkdir()
    run(["bash", str(repo / "tools" / "install_aris_kimi.sh"), str(project), "--quiet"])
    assert (project / ".agents" / "skills" / "alpha").is_symlink()
    assert not (project / ".agents" / "skills" / "gamma").exists()

    sha_v2 = bump_repo(repo)

    result = run(
        [
            "bash",
            str(repo / "tools" / "smart_update_kimi.sh"),
            "--apply",
            "--project",
            str(project),
            "--add-new",
        ]
    )

    assert result.returncode == 0, result.stderr
    assert head_sha(repo) == sha_v2
    gamma = project / ".agents" / "skills" / "gamma"
    assert gamma.is_symlink()
    assert (gamma / "SKILL.md").read_text() == "# kimi gamma v2\n"


def test_smart_update_kimi_refuses_dirty_clone(tmp_path: Path) -> None:
    repo = make_git_aris_repo(tmp_path)
    bump_repo(repo)
    (repo / "AGENT_GUIDE.md").write_text("# locally modified\n")

    result = run(
        ["bash", str(repo / "tools" / "smart_update_kimi.sh"), "--apply"],
        check=False,
    )

    assert result.returncode == 1
    assert "uncommitted tracked changes" in result.stderr
    assert head_sha(repo) == git(repo, "rev-parse", "business-research-suite-v0.0.1").stdout.strip()


def test_smart_update_kimi_legacy_kimi_tag_still_matches(tmp_path: Path) -> None:
    """Pre-unification clones only have -kimi-* tags; the default must still find them."""
    repo = make_git_aris_repo(tmp_path, tag="business-research-suite-kimi-v0.0.1")
    bump_repo(repo, tag="business-research-suite-kimi-v0.0.2")

    result = run(["bash", str(repo / "tools" / "smart_update_kimi.sh")])

    assert result.returncode == 0
    assert "business-research-suite-kimi-v0.0.2" in result.stdout


def test_smart_update_kimi_avoids_bash4_associative_arrays() -> None:
    """bash 3.2 (macOS stock bash) regression: no associative arrays."""
    assert "declare -A" not in UPDATE_SCRIPT.read_text()
