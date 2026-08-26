"""Mirror tests for the Kimi Code CLI native package (skills/skills-kimi).

Parity contract with skills/skills-codex (see tests/test_codex_skill_mirror.py):

- same skill-name set and same shared-reference name set;
- the 24 portable business skills + 9 portable shared references are
  byte-for-byte identical to canonical skills/ (same source set as
  tools/sync_business_portable_mirror.py);
- non-portable files carry no Codex residue (the generator refuses to emit
  any, and these tests re-scan the package);
- every Codex spawn_agent/send_input reviewer contract has a Kimi Agent-tool
  subagent contract (kimi_subagent / kimi_subagent_continue) in the mirror;
- reviewer honesty matches the Codex base package: same-family provisional.
"""

from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
from pathlib import Path

from tools.sync_business_portable_mirror import (
    PORTABLE_REFERENCES,
    PORTABLE_SKILLS,
    included_files,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
MAIN_SKILLS = REPO_ROOT / "skills"
CODEX_SKILLS = REPO_ROOT / "skills" / "skills-codex"
KIMI_SKILLS = REPO_ROOT / "skills" / "skills-kimi"

BOM = b"\xef\xbb\xbf"

# Factual external references allowed verbatim in the Kimi package (mirrors
# AUDIT_WHITELIST in tools/build_skills_kimi.py).
LEAK_WHITELIST = (
    "Codex app-server",
    "codex-image2",
    "gpt-5.5-pro",
    "GPT-5.5 Pro",
)

LEAK_PATTERNS = {
    "spawn_agent": r"spawn_agent",
    "send_input": r"send_input",
    "mcp__codex*": r"mcp__codex",
    "chrome:control-chrome": r"chrome:control-chrome",
    "codex_native_chrome": r"codex_native_chrome",
    "~/.codex": r"~/\.codex",
    ".codex/ path": r"\.codex/",
    "reasoning_effort": r"reasoning_effort",
    "xhigh effort": r"\bxhigh\b",
    "ultra effort": r"\bultra\b",
    "gpt-5.x model name": r"(?i)gpt-5",
    "skills-codex": r"skills-codex",
    "installed-skills-codex.txt": r"installed-skills-codex",
    "installed-skills.txt": r"installed-skills\.txt",
    "install_aris_codex": r"install_aris_codex",
    "Codex": r"\bCodex\b",
    "codex": r"\bcodex\b",
}

SPAWN_BLOCK = re.compile(r"(?m)^\s*spawn_agent:")
SEND_BLOCK = re.compile(r"(?m)^\s*send_input:")
KIMI_SPAWN = re.compile(r"(?m)^\s*kimi_subagent:")
KIMI_CONTINUE = re.compile(r"(?m)^\s*kimi_subagent_continue:")

# novelty-check's Codex source carries a degenerate fence containing only
# `reasoning_effort: xhigh` (no `spawn_agent:` header); the Kimi generator
# upgrades it to a full kimi_subagent block, so the marker parity is one-way
# there.
EXTRA_KIMI_MARKERS_ALLOWED = {"novelty-check"}


def skill_names(root: Path) -> set[str]:
    return {path.parent.name for path in root.glob("*/SKILL.md")}


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def non_portable_markdown(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in sorted(root.rglob("*.md")):
        rel = path.relative_to(root)
        # Package READMEs legitimately name the sibling skills-codex line.
        if rel.parts[0] in ("README.md", "README_CN.md"):
            continue
        if rel.parts[0] in PORTABLE_SKILLS:
            continue
        if rel.parts[0] == "shared-references" and rel.name in PORTABLE_REFERENCES:
            continue
        files.append(path)
    return files


def test_kimi_skill_set_matches_codex_line() -> None:
    main_names = skill_names(MAIN_SKILLS)
    codex_names = skill_names(CODEX_SKILLS)
    kimi_names = skill_names(KIMI_SKILLS)
    assert len(main_names) == 106
    assert kimi_names == codex_names == main_names


def test_kimi_shared_reference_set_matches_codex_line() -> None:
    codex_refs = {p.name for p in (CODEX_SKILLS / "shared-references").glob("*.md")}
    kimi_refs = {p.name for p in (KIMI_SKILLS / "shared-references").glob("*.md")}
    assert len(codex_refs) == 41
    assert kimi_refs == codex_refs


def test_kimi_portable_set_is_byte_identical_to_canonical() -> None:
    """The portable business suite must not diverge between canonical,
    skills-codex, and skills-kimi — all three are byte-for-byte copies."""
    assert len(PORTABLE_SKILLS) == 24
    assert len(PORTABLE_REFERENCES) == 10
    for name in PORTABLE_SKILLS:
        assert included_files(MAIN_SKILLS / name) == included_files(KIMI_SKILLS / name), name
    for name in PORTABLE_REFERENCES:
        canonical = (MAIN_SKILLS / "shared-references" / name).read_bytes()
        packaged = (KIMI_SKILLS / "shared-references" / name).read_bytes()
        assert packaged == canonical, name


def test_kimi_package_regeneration_is_idempotent() -> None:
    result = subprocess.run(
        [sys.executable, "tools/build_skills_kimi.py", "--check"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "106 skills" in result.stdout


def test_kimi_no_codex_leaks_in_non_portable_files() -> None:
    offenders: list[str] = []
    for path in non_portable_markdown(KIMI_SKILLS):
        text = read(path)
        for allowed in LEAK_WHITELIST:
            text = text.replace(allowed, "")
        for label, pattern in LEAK_PATTERNS.items():
            if re.search(pattern, text):
                offenders.append(f"{path.relative_to(REPO_ROOT)}: leaked {label}")
    assert not offenders, "skills-kimi non-portable files retain Codex residue:\n" + "\n".join(offenders)


def test_kimi_skill_files_have_no_bom() -> None:
    offenders = [
        str(path.relative_to(REPO_ROOT))
        for path in KIMI_SKILLS.glob("*/SKILL.md")
        if path.read_bytes().startswith(BOM)
    ]
    assert not offenders, "Kimi SKILL.md starts with UTF-8 BOM:\n" + "\n".join(offenders)


def test_kimi_reviewer_contract_partition() -> None:
    """Every Codex reviewer-protocol block has a Kimi subagent equivalent."""
    codex_names = skill_names(CODEX_SKILLS)
    multi_round: set[str] = set()
    single_round: set[str] = set()
    non_reviewer: set[str] = set()

    for name in codex_names:
        text = read(CODEX_SKILLS / name / "SKILL.md")
        spawn = SPAWN_BLOCK.search(text) is not None
        send = SEND_BLOCK.search(text) is not None
        if spawn and send:
            multi_round.add(name)
        elif spawn:
            single_round.add(name)
        else:
            non_reviewer.add(name)

    assert multi_round and single_round and non_reviewer

    for name in multi_round | single_round:
        kimi = read(KIMI_SKILLS / name / "SKILL.md")
        assert KIMI_SPAWN.search(kimi), f"{name}: missing kimi_subagent round-1 contract"

    for name in multi_round:
        kimi = read(KIMI_SKILLS / name / "SKILL.md")
        assert KIMI_CONTINUE.search(kimi), f"{name}: missing kimi_subagent_continue contract"
        assert re.search(r"(?m)^\s*resume:\s*\[saved", kimi), \
            f"{name}: continuation must resume the saved reviewer subagent"

    for name in non_reviewer:
        kimi = read(KIMI_SKILLS / name / "SKILL.md")
        if name in EXTRA_KIMI_MARKERS_ALLOWED:
            continue
        assert not KIMI_SPAWN.search(kimi), f"{name}: unexpected kimi_subagent marker"
        assert not KIMI_CONTINUE.search(kimi), f"{name}: unexpected kimi_subagent_continue marker"


def test_kimi_review_assurance_is_explicit_and_honest() -> None:
    routing = read(KIMI_SKILLS / "shared-references" / "reviewer-routing.md")
    tracing = read(KIMI_SKILLS / "shared-references" / "review-tracing.md")
    assert "review_independence: same-family" in routing
    assert "acceptance_status: provisional" in routing
    assert "kimi_subagent" in routing
    # The declared cross-family accepted upgrade path is llm-chat.
    assert "mcp__llm-chat__review" in routing
    assert "cross-family" in routing and "accepted" in routing
    assert '"review_independence": "same-family"' in tracing
    assert '"acceptance_status": "provisional"' in tracing

    # Same honesty floor as the Codex base package: these skills must document
    # that their base reviewer output is provisional.
    provisional_skills = {
        "auto-review-loop", "research-review", "paper-writing", "render-html",
        "proof-checker", "paper-claim-audit", "citation-audit", "kill-argument",
        "experiment-audit", "result-to-claim", "meta-apply",
    }
    for skill in sorted(provisional_skills):
        text = read(KIMI_SKILLS / skill / "SKILL.md")
        assert "provisional" in text, f"{skill} must document same-family provisional output"

    # No base-package file may dress the same-family subagent review up as
    # cross-family acceptance (adapted from the Codex mirror's forbidden list).
    forbidden = (
        "fresh cross-family Kimi",
        "Cross-model Kimi",
        "already cross-model-reviewed",
        "Cross-model independence",
        "cross-model review (Kimi",
    )
    offenders: list[str] = []
    for skill_file in KIMI_SKILLS.glob("*/SKILL.md"):
        text = read(skill_file)
        for phrase in forbidden:
            if phrase.lower() in text.lower():
                offenders.append(f"{skill_file.relative_to(REPO_ROOT)}: {phrase}")
    assert not offenders, "Kimi base package falsely claims cross-family review:\n" + "\n".join(offenders)

    experiment_audit = read(KIMI_SKILLS / "experiment-audit" / "SKILL.md")
    for field in (
        "executor_model", "executor_family", "reviewer_model", "reviewer_family",
        "review_independence", "acceptance_status", "trace_path", "verdict_id",
    ):
        assert field in experiment_audit, f"experiment-audit must emit {field}"

    result_to_claim = read(KIMI_SKILLS / "result-to-claim" / "SKILL.md")
    assert "traced `BLOCKED` review record" in result_to_claim
    assert "do not block the pipeline" not in result_to_claim


def test_kimi_manifest_name_does_not_leak() -> None:
    offenders: list[str] = []
    for path in KIMI_SKILLS.rglob("*"):
        if not path.is_file() or path.suffix not in (".md", ".py", ".sh"):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "installed-skills-codex" in text or "installed-skills.txt" in text:
            offenders.append(str(path.relative_to(REPO_ROOT)))
    assert not offenders, "Kimi package references another line's manifest:\n" + "\n".join(offenders)

    # The Kimi manifest name is actually used by the helper-resolution chains.
    assert ".aris/installed-skills-kimi.txt" in read(KIMI_SKILLS / "research-wiki" / "SKILL.md")
    assert ".aris/installed-skills-kimi.txt" in read(KIMI_SKILLS / "paper-writing" / "SKILL.md")


def test_kimi_shared_reference_links_resolve() -> None:
    failures: list[str] = []
    pattern = re.compile(r"\.\./shared-references/([A-Za-z0-9._-]+\.md)")
    for skill_file in KIMI_SKILLS.glob("*/SKILL.md"):
        for ref_name in pattern.findall(read(skill_file)):
            if not (KIMI_SKILLS / "shared-references" / ref_name).exists():
                failures.append(f"{skill_file.relative_to(REPO_ROOT)} -> shared-references/{ref_name}")
    assert not failures, "Kimi skill shared-reference links must resolve inside skills-kimi:\n" + "\n".join(failures)


def test_kimi_render_html_strips_bom_frontmatter() -> None:
    script = KIMI_SKILLS / "render-html" / "scripts" / "render_html.py"
    spec = importlib.util.spec_from_file_location("kimi_render_html", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    markdown = "\ufeff---\ntitle: Draft\n---\n# Body\n"

    assert module.strip_frontmatter(markdown) == "# Body\n"


def test_kimi_readme_positions_the_package() -> None:
    readme = read(KIMI_SKILLS / "README.md")
    assert "Kimi Code CLI" in readme
    assert "kimi_subagent" in readme
    assert "review_independence: same-family" in readme
    assert "acceptance_status: provisional" in readme
    assert "llm-chat" in readme
    assert "install_aris_kimi.sh" in readme
    assert "installed-skills-kimi.txt" in readme
    assert "~/.kimi-code/skills/" in readme
    assert "`106`" in readme
