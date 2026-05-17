from __future__ import annotations

import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALL_SCRIPT = REPO_ROOT / "tools" / "install_business_codex_skills.sh"

EXPECTED_ENTRIES = {
    "business-lit-review",
    "business-idea-creator",
    "business-novelty-check",
    "empirical-design-plan",
    "data-analysis-bridge",
    "r-analysis-bridge",
    "stata-analysis-bridge",
    "evidence-to-claim",
    "business-number-audit",
    "business-paper-plan",
    "business-paper-writing",
    "business-rebuttal",
    "business-research-pipeline",
    "shared-references",
}


def run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=check,
    )


def test_business_codex_install_dry_run_has_no_project_writes(tmp_path: Path) -> None:
    project = tmp_path / "paper-project"

    result = run(
        [
            "bash",
            str(INSTALL_SCRIPT),
            str(project),
            "--aris-repo",
            str(REPO_ROOT),
            "--dry-run",
        ]
    )

    assert "Business-only Codex skill install plan" in result.stdout
    assert "(dry-run) no changes made" in result.stdout
    assert not (project / ".agents").exists()
    assert not (project / ".aris").exists()


def test_business_codex_install_reconcile_and_uninstall(tmp_path: Path) -> None:
    project = tmp_path / "paper-project"

    run(
        [
            "bash",
            str(INSTALL_SCRIPT),
            str(project),
            "--aris-repo",
            str(REPO_ROOT),
            "--quiet",
        ]
    )

    skills_dir = project / ".agents" / "skills"
    installed = {path.name for path in skills_dir.iterdir()}
    assert installed == EXPECTED_ENTRIES
    assert not (skills_dir / "research-pipeline").exists()
    assert not (skills_dir / "experiment-bridge").exists()
    assert (skills_dir / "business-lit-review").is_symlink()
    assert (skills_dir / "r-analysis-bridge").is_symlink()
    assert (skills_dir / "shared-references").is_symlink()

    manifest = project / ".aris" / "installed-business-skills-codex.txt"
    assert manifest.exists()
    manifest_text = manifest.read_text()
    assert "profile\tbusiness-codex" in manifest_text
    assert "entry\tbusiness-research-pipeline" in manifest_text
    assert "entry\tresearch-pipeline" not in manifest_text

    agents_text = (project / "AGENTS.md").read_text()
    assert "ARIS Business Codex Skill Scope" in agents_text
    assert "business/accounting/finance workflow skills" in agents_text

    local_only = skills_dir / "local-only"
    local_only.mkdir()

    run(
        [
            "bash",
            str(INSTALL_SCRIPT),
            str(project),
            "--aris-repo",
            str(REPO_ROOT),
            "--reconcile",
            "--quiet",
        ]
    )
    assert local_only.exists()

    run(
        [
            "bash",
            str(INSTALL_SCRIPT),
            str(project),
            "--uninstall",
            "--quiet",
        ]
    )
    assert local_only.exists()
    for entry in EXPECTED_ENTRIES:
        assert not (skills_dir / entry).exists()
    assert not manifest.exists()
    assert (project / ".aris" / "installed-business-skills-codex.txt.prev").exists()
    assert "ARIS Business Codex Skill Scope" not in (project / "AGENTS.md").read_text()


def test_business_codex_install_refuses_full_codex_manifest(tmp_path: Path) -> None:
    project = tmp_path / "paper-project"
    aris = project / ".aris"
    aris.mkdir(parents=True)
    (aris / "installed-skills-codex.txt").write_text("profile\tfull-codex\n")

    result = run(
        [
            "bash",
            str(INSTALL_SCRIPT),
            str(project),
            "--aris-repo",
            str(REPO_ROOT),
        ],
        check=False,
    )

    assert result.returncode != 0
    assert "full Codex install manifest exists" in result.stderr
    assert not (project / ".agents").exists()
