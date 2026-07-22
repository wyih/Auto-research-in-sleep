from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    ("installer_name", "installed_relative", "extra_args"),
    (
        (
            "install_aris.sh",
            Path(".claude/skills/results-to-docx"),
            (),
        ),
        (
            "install_aris_codex.sh",
            Path(".agents/skills/results-to-docx"),
            ("--no-global-pointer",),
        ),
        (
            "install_aris_copilot.sh",
            Path(".github/skills/results-to-docx"),
            (),
        ),
    ),
)
def test_bash_installers_require_and_store_explicit_office_author(
    tmp_path: Path,
    installer_name: str,
    installed_relative: Path,
    extra_args: tuple[str, ...],
) -> None:
    installer = REPO_ROOT / "tools" / installer_name
    identity_file = tmp_path / "user-config" / "office-author"
    environment = os.environ.copy()
    environment["HOME"] = str(tmp_path / "home")
    environment["ARIS_OFFICE_AUTHOR_FILE"] = str(identity_file)

    missing_project = tmp_path / "missing-project"
    missing_project.mkdir()
    common = [
        "bash",
        str(installer),
        str(missing_project),
        "--aris-repo",
        str(REPO_ROOT),
        "--skills",
        "results-to-docx",
        "--quiet",
        "--no-doc",
        *extra_args,
    ]
    missing = subprocess.run(
        common,
        cwd=REPO_ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    assert missing.returncode != 0
    assert "office-author NAME is required" in (missing.stdout + missing.stderr)
    assert not identity_file.exists()
    assert not (missing_project / installed_relative).exists()

    installed_project = tmp_path / "installed-project"
    installed_project.mkdir()
    applied = subprocess.run(
        [
            "bash",
            str(installer),
            str(installed_project),
            "--aris-repo",
            str(REPO_ROOT),
            "--skills",
            "results-to-docx",
            "--quiet",
            "--no-doc",
            *extra_args,
            "--office-author",
            "  Installer Test Author  ",
        ],
        cwd=REPO_ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    assert applied.returncode == 0, applied.stdout + applied.stderr
    assert (installed_project / installed_relative).is_symlink()
    assert identity_file.read_text(encoding="utf-8") == "Installer Test Author\n"
    assert stat.S_IMODE(identity_file.stat().st_mode) == 0o600
    assert not (installed_project / ".aris" / "office-author").exists()
