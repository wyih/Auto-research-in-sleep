"""Tests for install_aris_kimi.sh (Kimi Code CLI install line)."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALL_SCRIPT = REPO_ROOT / "tools" / "install_aris_kimi.sh"
CODEX_INSTALL_SCRIPT = REPO_ROOT / "tools" / "install_aris_codex.sh"


def run(
    cmd: list[str], *, cwd: Path | None = None, check: bool = True, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd or REPO_ROOT,
        text=True,
        capture_output=True,
        check=check,
        env=env,
    )


def make_skill(path: Path, body: str) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "SKILL.md").write_text(body)


def make_minimal_aris_repo(root: Path) -> Path:
    """Minimal ARIS repo with diverged skills-kimi and skills-codex packages.

    skills-kimi is the Kimi install source; skills-codex exists so the codex
    installer can manage the same project in coexistence tests. Mainline
    skills/ and the review overlay packages exist to prove they are NOT
    scanned as Kimi skills.
    """
    repo = root / "aris"
    # Kimi-native package (install source)
    make_skill(repo / "skills" / "skills-kimi" / "alpha", "# kimi alpha\n")
    make_skill(repo / "skills" / "skills-kimi" / "beta", "# kimi beta\n")
    make_skill(repo / "skills" / "skills-kimi" / "gamma", "# kimi gamma\n")
    (repo / "skills" / "skills-kimi" / "shared-references").mkdir(parents=True, exist_ok=True)
    (repo / "skills" / "skills-kimi" / "shared-references" / "reviewer-routing.md").write_text("kimi routing\n")
    # Codex package (diverged content, same skill names)
    make_skill(repo / "skills" / "skills-codex" / "alpha", "# codex alpha\n")
    make_skill(repo / "skills" / "skills-codex" / "beta", "# codex beta\n")
    make_skill(repo / "skills" / "skills-codex" / "gamma", "# codex gamma\n")
    (repo / "skills" / "skills-codex" / "shared-references").mkdir(parents=True, exist_ok=True)
    (repo / "skills" / "skills-codex" / "shared-references" / "reviewer-routing.md").write_text("codex routing\n")
    # Mainline + overlay packages: must NOT be installed by the Kimi line.
    make_skill(repo / "skills" / "alpha", "# mainline alpha\n")
    make_skill(repo / "skills" / "skills-codex-claude-review" / "beta", "# beta-claude-overlay\n")
    make_skill(repo / "skills" / "skills-codex-gemini-review" / "beta", "# beta-gemini-overlay\n")
    # AGENT_GUIDE.md for repo discovery parity with other installers
    (repo / "AGENT_GUIDE.md").write_text("# Agent Guide\n")
    return repo


def manifest_rows(manifest: Path) -> dict[str, str]:
    """name -> mode for body rows of an ARIS install manifest."""
    text = manifest.read_text()
    rows: dict[str, str] = {}
    in_body = False
    for line in text.splitlines():
        if line == "kind\tname\tsource_rel\ttarget_rel\tmode":
            in_body = True
            continue
        if in_body and line.count("\t") == 4:
            _kind, name, _source, _target, mode = line.split("\t")
            rows[name] = mode
    return rows


def kimi_install(project: Path, repo: Path, *extra: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return run(
        ["bash", str(INSTALL_SCRIPT), str(project), "--aris-repo", str(repo), *extra],
        check=check,
    )


def codex_install(project: Path, repo: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return run(
        ["bash", str(CODEX_INSTALL_SCRIPT), str(project), "--aris-repo", str(repo), *extra],
    )


def test_install_kimi_dry_run_has_no_project_writes(tmp_path: Path) -> None:
    repo = make_minimal_aris_repo(tmp_path)
    project = tmp_path / "project"
    project.mkdir()

    dry_run = kimi_install(project, repo, "--dry-run")

    assert "(dry-run) no changes made" in dry_run.stdout
    assert not (project / ".aris").exists()
    assert not (project / ".agents").exists()
    assert not (project / "AGENTS.md").exists()


def test_install_kimi_avoids_bash4_associative_arrays() -> None:
    """bash 3.2 (macOS stock bash) regression: no associative arrays."""
    text = INSTALL_SCRIPT.read_text()
    assert "declare -A" not in text


def test_install_kimi_empty_replace_link_array_under_set_u(tmp_path: Path) -> None:
    """bash 3.2 regression: no --replace-link must not trip `set -u`."""
    repo = make_minimal_aris_repo(tmp_path)
    project = tmp_path / "project"
    project.mkdir()

    result = kimi_install(project, repo, "--quiet")

    assert result.returncode == 0
    assert "unbound variable" not in (result.stdout + result.stderr)


def test_install_kimi_creates_symlinks_manifest_and_agents_block(tmp_path: Path) -> None:
    repo = make_minimal_aris_repo(tmp_path)
    project = tmp_path / "project"
    project.mkdir()

    kimi_install(project, repo, "--quiet")

    manifest = project / ".aris" / "installed-skills-kimi.txt"
    assert manifest.exists()
    manifest_text = manifest.read_text()
    assert "repo_root" in manifest_text
    assert "installer\tinstall_aris_kimi.sh" in manifest_text
    assert "packages\tskills-kimi" in manifest_text

    agents_text = (project / "AGENTS.md").read_text()
    assert "ARIS-KIMI:BEGIN" in agents_text
    assert "ARIS Kimi Code Skill Scope" in agents_text
    assert f"ARIS repo root: `{repo}`" in agents_text

    # Symlinks point at skills/skills-kimi/<name> — the Kimi-native package
    for name in ("alpha", "beta", "gamma"):
        link = project / ".agents" / "skills" / name
        assert link.is_symlink()
        assert link.resolve() == (repo / "skills" / "skills-kimi" / name)
    assert (project / ".agents" / "skills" / "shared-references").resolve() == (
        repo / "skills" / "skills-kimi" / "shared-references"
    )

    # Package dirs themselves and other release lines are never installed
    installed = [p.name for p in (project / ".agents" / "skills").iterdir()]
    for excluded in ("skills-kimi", "skills-codex", "skills-codex-claude-review", "skills-codex-gemini-review"):
        assert excluded not in installed
    assert (project / ".agents" / "skills" / "alpha").resolve() != (repo / "skills" / "alpha")
    assert (project / ".agents" / "skills" / "alpha").resolve() != (repo / "skills" / "skills-codex" / "alpha")


def test_install_kimi_reinstall_is_idempotent(tmp_path: Path) -> None:
    repo = make_minimal_aris_repo(tmp_path)
    project = tmp_path / "project"
    project.mkdir()

    kimi_install(project, repo, "--quiet")
    first_rows = manifest_rows(project / ".aris" / "installed-skills-kimi.txt")

    second = kimi_install(project, repo, "--quiet")
    assert second.returncode == 0
    # Reinstall keeps every link and the same managed set
    for name in ("alpha", "beta", "gamma", "shared-references"):
        link = project / ".agents" / "skills" / name
        assert link.is_symlink()
        assert link.resolve() == (repo / "skills" / "skills-kimi" / name)
    assert manifest_rows(project / ".aris" / "installed-skills-kimi.txt") == first_rows


def test_install_kimi_reconcile_adds_and_removes(tmp_path: Path) -> None:
    repo = make_minimal_aris_repo(tmp_path)
    project = tmp_path / "project"
    project.mkdir()

    kimi_install(project, repo, "--quiet")
    assert (project / ".agents" / "skills" / "alpha").is_symlink()

    (repo / "skills" / "skills-kimi" / "alpha" / "SKILL.md").unlink()
    (repo / "skills" / "skills-kimi" / "alpha").rmdir()
    make_skill(repo / "skills" / "skills-kimi" / "delta", "# kimi delta\n")

    kimi_install(project, repo, "--reconcile", "--add-new", "--quiet")

    assert not (project / ".agents" / "skills" / "alpha").exists()
    assert (project / ".agents" / "skills" / "delta").is_symlink()
    assert (project / ".agents" / "skills" / "delta").resolve() == (repo / "skills" / "skills-kimi" / "delta")
    assert (project / ".agents" / "skills" / "beta").is_symlink()


def test_install_kimi_uninstall_removes_managed_only(tmp_path: Path) -> None:
    repo = make_minimal_aris_repo(tmp_path)
    project = tmp_path / "project"
    project.mkdir()

    kimi_install(project, repo, "--quiet")

    (project / ".agents" / "skills" / "my-custom-skill").mkdir(parents=True)
    (project / ".agents" / "skills" / "my-custom-skill" / "SKILL.md").write_text("# mine\n")

    kimi_install(project, repo, "--uninstall", "--quiet")

    assert (project / ".agents" / "skills" / "my-custom-skill").exists()
    assert not (project / ".agents" / "skills" / "alpha").exists()
    assert not (project / ".agents" / "skills" / "beta").exists()
    assert (project / ".aris" / "installed-skills-kimi.txt.prev").exists()
    assert not (project / ".aris" / "installed-skills-kimi.txt").exists()
    assert "ARIS Kimi Code Skill Scope" not in (project / "AGENTS.md").read_text()


def test_install_kimi_conflict_on_real_path(tmp_path: Path) -> None:
    repo = make_minimal_aris_repo(tmp_path)
    project = tmp_path / "project"
    project.mkdir()

    (project / ".agents" / "skills" / "alpha").mkdir(parents=True)
    (project / ".agents" / "skills" / "alpha" / "SKILL.md").write_text("# local\n")

    result = kimi_install(project, repo, "--quiet", check=False)

    assert result.returncode != 0
    combined = result.stdout + result.stderr
    assert "CONFLICT" in combined or "conflict" in combined.lower()


def test_install_kimi_conflicts_with_codex_managed_names(tmp_path: Path) -> None:
    """Codex-managed names hard-fail as CONFLICT — the two lines diverged."""
    repo = make_minimal_aris_repo(tmp_path)
    project = tmp_path / "project"
    project.mkdir()

    codex_install(project, repo, "--quiet")
    codex_manifest_before = (project / ".aris" / "installed-skills-codex.txt").read_text()

    result = kimi_install(project, repo, "--quiet", check=False)

    assert result.returncode != 0
    combined = result.stdout + result.stderr
    assert "codex_managed" in combined
    # Error text prescribes the exact switch-lines procedure
    assert "install_aris_codex.sh" in combined
    assert "--uninstall" in combined
    # Nothing was written: no kimi manifest, codex manifest + links untouched
    assert not (project / ".aris" / "installed-skills-kimi.txt").exists()
    assert (project / ".aris" / "installed-skills-codex.txt").read_text() == codex_manifest_before
    for name in ("alpha", "beta", "gamma"):
        link = project / ".agents" / "skills" / name
        assert link.is_symlink()
        assert link.resolve() == (repo / "skills" / "skills-codex" / name)


def test_install_kimi_conflict_only_for_selected_codex_names(tmp_path: Path) -> None:
    """A codex-managed name the Kimi selection does not need is left alone."""
    repo = make_minimal_aris_repo(tmp_path)
    project = tmp_path / "project"
    (project / ".agents" / "skills").mkdir(parents=True)
    (project / ".aris").mkdir(parents=True)

    # Codex line manages only `alpha` here (hand-written manifest, format v1).
    (project / ".agents" / "skills" / "alpha").symlink_to(repo / "skills" / "skills-codex" / "alpha")
    (project / ".aris" / "installed-skills-codex.txt").write_text(
        "version\t1\n"
        f"repo_root\t{repo}\n"
        f"project_root\t{project}\n"
        "installer\tinstall_aris_codex.sh\n"
        "kind\tname\tsource_rel\ttarget_rel\tmode\n"
        "skill\talpha\tskills/skills-codex/alpha\t.agents/skills/alpha\tsymlink\n"
    )

    # Select a real kimi skill NOT managed by codex.
    make_skill(repo / "skills" / "skills-kimi" / "kimi-only", "# kimi only\n")
    result = kimi_install(project, repo, "--skills", "kimi-only", "--quiet")
    assert result.returncode == 0
    assert (project / ".agents" / "skills" / "kimi-only").resolve() == (
        repo / "skills" / "skills-kimi" / "kimi-only"
    )
    rows = manifest_rows(project / ".aris" / "installed-skills-kimi.txt")
    assert "kimi-only" in rows
    assert "alpha" not in rows
    # Codex entry untouched
    assert (project / ".agents" / "skills" / "alpha").resolve() == (repo / "skills" / "skills-codex" / "alpha")

    # Selecting the codex-managed name itself hard-fails.
    conflict = kimi_install(project, repo, "--skills", "alpha", "--quiet", check=False)
    assert conflict.returncode != 0
    assert "codex_managed" in (conflict.stdout + conflict.stderr)


def test_switch_lines_codex_uninstall_then_kimi_install(tmp_path: Path) -> None:
    """Switching lines: codex uninstall frees the names for the Kimi line."""
    repo = make_minimal_aris_repo(tmp_path)
    project = tmp_path / "project"
    project.mkdir()

    codex_install(project, repo, "--quiet")
    # Kimi install is refused while Codex owns the names
    refused = kimi_install(project, repo, "--quiet", check=False)
    assert refused.returncode != 0

    codex_install(project, repo, "--uninstall", "--quiet")
    assert not (project / ".agents" / "skills" / "alpha").exists()

    kimi_install(project, repo, "--quiet")
    assert (project / ".agents" / "skills" / "alpha").resolve() == (repo / "skills" / "skills-kimi" / "alpha")
    assert manifest_rows(project / ".aris" / "installed-skills-kimi.txt")["alpha"] == "symlink"

    # And back: kimi uninstall frees them for the Codex line again
    kimi_install(project, repo, "--uninstall", "--quiet")
    codex_install(project, repo, "--quiet")
    assert (project / ".agents" / "skills" / "alpha").resolve() == (repo / "skills" / "skills-codex" / "alpha")


def test_install_kimi_uninstall_keeps_legacy_shared_codex_entries(tmp_path: Path) -> None:
    """Legacy manifests with shared-codex rows uninstall without touching Codex."""
    repo = make_minimal_aris_repo(tmp_path)
    project = tmp_path / "project"
    project.mkdir()

    codex_install(project, repo, "--quiet")
    codex_manifest_before = (project / ".aris" / "installed-skills-codex.txt").read_text()

    # Hand-craft a pre-divergence kimi manifest marking alpha as shared-codex
    # and beta as a kimi-owned symlink pointing at the skills-kimi package.
    skills_rel = ".agents/skills"
    (project / ".agents" / "skills" / "beta").unlink()
    (project / ".agents" / "skills" / "beta").symlink_to(repo / "skills" / "skills-kimi" / "beta")
    (project / ".aris" / "installed-skills-kimi.txt").write_text(
        "version\t1\n"
        f"repo_root\t{repo}\n"
        f"project_root\t{project}\n"
        "installer\tinstall_aris_kimi.sh\n"
        "kind\tname\tsource_rel\ttarget_rel\tmode\n"
        f"skill\talpha\tskills/skills-codex/alpha\t{skills_rel}/alpha\tshared-codex\n"
        f"skill\tbeta\tskills/skills-kimi/beta\t{skills_rel}/beta\tsymlink\n"
    )

    kimi_install(project, repo, "--uninstall", "--quiet")

    # shared-codex row kept on disk; kimi-owned row removed
    assert (project / ".agents" / "skills" / "alpha").is_symlink()
    assert (project / ".agents" / "skills" / "alpha").resolve() == (repo / "skills" / "skills-codex" / "alpha")
    assert not (project / ".agents" / "skills" / "beta").exists()
    assert (project / ".aris" / "installed-skills-codex.txt").read_text() == codex_manifest_before
    assert not (project / ".aris" / "installed-skills-kimi.txt").exists()
    assert (project / ".aris" / "installed-skills-kimi.txt.prev").exists()


def test_install_kimi_global_scope(tmp_path: Path) -> None:
    """--global installs to ~/.kimi-code/skills with manifest under ~/.aris."""
    repo = make_minimal_aris_repo(tmp_path)
    home = tmp_path / "home"
    home.mkdir()
    env = os.environ.copy()
    env["HOME"] = str(home)

    run(
        [
            "bash",
            str(INSTALL_SCRIPT),
            "--global",
            "--aris-repo",
            str(repo),
            "--quiet",
            "--no-global-pointer",
        ],
        env=env,
    )

    assert (home / ".kimi-code" / "skills" / "alpha").is_symlink()
    assert (home / ".kimi-code" / "skills" / "alpha").resolve() == (repo / "skills" / "skills-kimi" / "alpha")
    manifest = home / ".aris" / "installed-skills-kimi.txt"
    assert manifest.exists()
    assert "scope\tglobal" in manifest.read_text()
    # No AGENTS.md written in global mode
    assert not (home / "AGENTS.md").exists()

    run(
        [
            "bash",
            str(INSTALL_SCRIPT),
            "--global",
            "--aris-repo",
            str(repo),
            "--uninstall",
            "--quiet",
            "--no-global-pointer",
        ],
        env=env,
    )

    assert not (home / ".kimi-code" / "skills" / "alpha").exists()
    assert not (home / ".aris" / "installed-skills-kimi.txt").exists()
    assert (home / ".aris" / "installed-skills-kimi.txt.prev").exists()


def test_install_kimi_prints_review_backend_note(tmp_path: Path) -> None:
    repo = make_minimal_aris_repo(tmp_path)
    project = tmp_path / "project"
    project.mkdir()

    # Non-quiet run prompts before applying; answer "y" to the apply prompt.
    result = subprocess.run(
        ["bash", str(INSTALL_SCRIPT), str(project), "--aris-repo", str(repo)],
        cwd=REPO_ROOT,
        input="y\n",
        text=True,
        capture_output=True,
        check=True,
    )

    assert "Reviewer-backend note (Kimi Code)" in result.stdout
    assert "kimi_subagent" in result.stdout
    assert "same-family" in result.stdout
    assert "mcp-servers/llm-chat" in result.stdout
    assert "docs/KIMI_ADAPTATION.md" in result.stdout
