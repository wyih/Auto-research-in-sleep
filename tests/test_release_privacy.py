from __future__ import annotations

import re
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MAC_HOME_COMPONENTS = {"...", "<name>", "me", "yourname", "你的用户名"}
LINUX_HOME_COMPONENTS = {"YOUR_USERNAME", "u", "user", "username", "用户名"}
BROWSER_STATE_NAMES = {
    "Cookies",
    "Cookies-journal",
    "History",
    "Local State",
    "Login Data",
    "Preferences",
    "Web Data",
}


def tracked_paths() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=REPO_ROOT,
        capture_output=True,
        check=True,
    )
    return [REPO_ROOT / item.decode("utf-8") for item in result.stdout.split(b"\0") if item]


def test_release_snapshot_has_no_maintainer_identity_or_machine_path() -> None:
    maintainer_name = "Yihong" + " Wang"
    maintainer_login = "wy" + "ih"
    encoded_login = "%2FUsers%2F" + maintainer_login
    banned_fragments = (
        maintainer_name,
        "/" + "Users" + "/" + maintainer_login,
        encoded_login,
    )
    mac_home = re.compile(re.escape("/" + "Users" + "/") + r"([^/\s`\"']+)")
    linux_home = re.compile(re.escape("/" + "home" + "/") + r"([^/\s`\"']+)")
    failures: list[str] = []

    for path in tracked_paths():
        text = path.read_bytes().decode("utf-8", errors="ignore")
        relative = path.relative_to(REPO_ROOT).as_posix()
        for fragment in banned_fragments:
            if fragment in text:
                failures.append(f"{relative}: maintainer identity or path")
        for match in mac_home.finditer(text):
            if match.group(1) not in MAC_HOME_COMPONENTS:
                failures.append(f"{relative}: non-placeholder macOS home path")
        for match in linux_home.finditer(text):
            if match.group(1) not in LINUX_HOME_COMPONENTS:
                failures.append(f"{relative}: non-placeholder Linux home path")

    assert failures == []


def test_release_snapshot_excludes_browser_state_and_secret_files() -> None:
    failures: list[str] = []
    for path in tracked_paths():
        relative = path.relative_to(REPO_ROOT)
        if relative.parts and relative.parts[0] == ".agents":
            failures.append(f"tracked agent-local state: {relative}")
        if path.name in BROWSER_STATE_NAMES:
            failures.append(f"tracked browser state: {relative}")
        if path.name == ".env" or (path.name.startswith(".env.") and path.name != ".env.example"):
            failures.append(f"tracked environment file: {relative}")
        if path.name in {"id_rsa", "id_ed25519"} or path.suffix.lower() in {
            ".p12",
            ".pfx",
            ".pem",
        }:
            failures.append(f"tracked credential file: {relative}")

    assert failures == []


def test_vast_gpu_examples_use_documentation_ip_range() -> None:
    for relative in (
        Path("skills/vast-gpu/SKILL.md"),
        Path("skills/skills-codex/vast-gpu/SKILL.md"),
    ):
        text = (REPO_ROOT / relative).read_text(encoding="utf-8")
        ssh_hosts = re.findall(r"ssh://root@([0-9.]+):", text)
        assert ssh_hosts
        assert set(ssh_hosts) == {"203.0.113.10"}


def test_skill_installers_do_not_rewrite_recipient_git_identity() -> None:
    for relative in (
        Path("tools/install_aris.sh"),
        Path("tools/install_aris.ps1"),
        Path("tools/install_aris_codex.sh"),
        Path("tools/install_aris_copilot.sh"),
    ):
        text = (REPO_ROOT / relative).read_text(encoding="utf-8")
        assert "git config user.name" not in text
        assert "git config user.email" not in text


def test_every_installer_requires_an_explicit_office_author_for_results() -> None:
    bash_installers = (
        Path("tools/install_aris.sh"),
        Path("tools/install_aris_codex.sh"),
        Path("tools/install_aris_copilot.sh"),
    )
    for relative in bash_installers:
        text = (REPO_ROOT / relative).read_text(encoding="utf-8")
        assert "--office-author NAME" in text
        assert 'in_file "results-to-docx"' in text
        assert "ARIS_OFFICE_AUTHOR_FILE" in text
        assert "write_office_author_config" in text

    powershell = (REPO_ROOT / "tools" / "install_aris.ps1").read_text(
        encoding="utf-8"
    )
    assert "[string]$OfficeAuthor" in powershell
    assert "Contains('results-to-docx')" in powershell
    assert "ARIS_OFFICE_AUTHOR_FILE" in powershell
    assert "Write-OfficeAuthorConfig" in powershell
