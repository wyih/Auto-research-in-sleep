from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CATALOG = REPO_ROOT / "tools" / "skill-groups.tsv"
INSTALLER = REPO_ROOT / "tools" / "install_aris_codex.sh"
PACKAGE_ROOT = REPO_ROOT / "skills" / "skills-codex"
TEST_SUITE_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "test-suite.yml"
sys.path.insert(0, str(REPO_ROOT))

from tools.sync_business_portable_mirror import (
    PORTABLE_REFERENCES,
    PORTABLE_SKILLS,
    check,
)


def test_portable_business_mirror_is_exact() -> None:
    assert len(PORTABLE_SKILLS) == 24
    assert len(PORTABLE_REFERENCES) == 9
    assert check() == []


def test_portable_business_mirror_check_is_cli_runnable() -> None:
    result = subprocess.run(
        [sys.executable, "tools/sync_business_portable_mirror.py", "--check"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "24 skills, 9 references" in result.stdout


def test_business_research_catalog_group_is_exact_portable_set() -> None:
    catalog_names = {
        fields[1]
        for line in CATALOG.read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#")
        if (fields := line.split("\t"))[0] == "skill" and fields[2] == "business-research"
    }

    assert catalog_names == set(PORTABLE_SKILLS)


def test_portable_package_documents_native_windows_and_wsl_separately() -> None:
    for readme_name in ("README.md", "README_CN.md"):
        text = (PACKAGE_ROOT / readme_name).read_text(encoding="utf-8")
        assert "--groups business-research --quiet" in text
        assert "install_aris.ps1" in text
        assert "-Platform codex" in text
        assert "-Groups business-research" in text
        assert "--office-author" in text
        assert "-OfficeAuthor" in text
        assert ".agents/skills" in text
        assert "release tag" in text
        assert "WSL 2" in text
        assert "WSLg" in text
        assert "/mnt/c" in text
        assert "Linux Chrome" in text
        assert "pdfinfo" in text
        assert "pdftotext" in text
        assert "poppler-utils" in text


def test_full_suite_ci_installs_pdf_verifiers_on_linux_and_macos() -> None:
    text = TEST_SUITE_WORKFLOW.read_text(encoding="utf-8")
    assert "if: runner.os == 'Linux'" in text
    assert "sudo apt-get update && sudo apt-get install -y poppler-utils" in text
    assert "if: runner.os == 'macOS'" in text
    assert "brew install poppler" in text



def test_business_group_install_is_exact_and_does_not_write_global_pointer(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    fake_home = tmp_path / "home"
    project.mkdir()
    fake_home.mkdir()
    env = os.environ.copy()
    env["HOME"] = str(fake_home)

    result = subprocess.run(
        [
            "bash",
            str(INSTALLER),
            str(project),
            "--aris-repo",
            str(REPO_ROOT),
            "--groups",
            "business-research",
            "--quiet",
            "--office-author",
            "Portable Test Author",
            "--no-doc",
            "--no-global-pointer",
        ],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    manifest = project / ".aris" / "installed-skills-codex.txt"
    manifest_names = {
        fields[1]
        for line in manifest.read_text(encoding="utf-8").splitlines()
        if (fields := line.split("\t"))[0] == "skill"
    }
    assert manifest_names == set(PORTABLE_SKILLS)
    assert not (project / "AGENTS.md").exists()
    assert not (fake_home / ".aris" / "repo").exists()
    assert (fake_home / ".aris" / "office-author").read_text(
        encoding="utf-8"
    ) == "Portable Test Author\n"

    installed_root = project / ".agents" / "skills"
    assert (installed_root / "shared-references").resolve() == PACKAGE_ROOT / "shared-references"
    assert {
        entry.name for entry in installed_root.iterdir() if entry.name != "shared-references"
    } == set(PORTABLE_SKILLS)
    for name in PORTABLE_SKILLS:
        assert (installed_root / name).is_symlink()
        assert (installed_root / name).resolve() == PACKAGE_ROOT / name
