#!/usr/bin/env python3
"""Normalize Author / Last Modified By metadata on generated DOCX files.

Edits package metadata only (core/app properties) and removes dormant
comment/people/custom-property parts and revision-session IDs that can retain
template or editor identity.
Document body text and table formatting are left unchanged.

Default author: Yihong Wang
"""

from __future__ import annotations

import argparse
import json
import os
import posixpath
import re
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

AUTHOR = "Yihong Wang"

NS_CP = "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
NS_DC = "http://purl.org/dc/elements/1.1/"
NS_DCTERMS = "http://purl.org/dc/terms/"
NS_DCMITYPE = "http://purl.org/dc/dcmitype/"
NS_EP = "http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
NS_VT = "http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"
NS_CT = "http://schemas.openxmlformats.org/package/2006/content-types"
NS_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
NS_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS_XSI = "http://www.w3.org/2001/XMLSchema-instance"

ET.register_namespace("cp", NS_CP)
ET.register_namespace("dc", NS_DC)
ET.register_namespace("dcterms", NS_DCTERMS)
ET.register_namespace("dcmitype", NS_DCMITYPE)
ET.register_namespace("xsi", NS_XSI)
ET.register_namespace("vt", NS_VT)
ET.register_namespace("w", NS_W)

COMMENT_PART_RE = re.compile(
    r"^word/(?:comments[^/]*\.xml|people\.xml|_rels/comments[^/]*\.xml\.rels)$"
)
COMMENT_MARKER_TAGS = {
    f"{{{NS_W}}}commentRangeStart",
    f"{{{NS_W}}}commentRangeEnd",
    f"{{{NS_W}}}commentReference",
}
RSID_ATTRIBUTE_RE = re.compile(br'\s+w:rsid[A-Za-z]*="[^"]*"')
COMMENT_MARKER_RE = re.compile(
    br"<w:(?:commentRangeStart|commentRangeEnd|commentReference)\b[^>]*/>"
)
TRACKED_CHANGE_PATTERNS = (
    re.compile(br"<w:ins(?:\s|>)"),
    re.compile(br"<w:del(?:\s|>)"),
    re.compile(br"<w:moveFrom(?:\s|>)"),
    re.compile(br"<w:moveTo(?:\s|>)"),
)


def _xml_bytes(root: ET.Element, default_namespace: str | None = None) -> bytes:
    if default_namespace is not None:
        ET.register_namespace("", default_namespace)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def _set_child_text(root: ET.Element, tag: str, value: str) -> None:
    node = root.find(tag)
    if node is None:
        node = ET.SubElement(root, tag)
    node.text = value


def _strip_comment_markers(data: bytes) -> bytes:
    # Byte-level removal preserves namespace declarations referenced only by
    # mc:Ignorable values (ElementTree would otherwise drop those declarations).
    cleaned = RSID_ATTRIBUTE_RE.sub(b"", data)
    cleaned = COMMENT_MARKER_RE.sub(b"", cleaned)
    if any(marker in cleaned for marker in (b"commentRange", b"commentReference")):
        # Fallback for unusual prefixes/non-empty marker serialization.
        root = ET.fromstring(cleaned)
        changed = False
        for parent in root.iter():
            for child in list(parent):
                if child.tag in COMMENT_MARKER_TAGS:
                    parent.remove(child)
                    changed = True
        if changed:
            return _xml_bytes(root)
    return cleaned


def _relationship_target(part_name: str, target: str) -> str:
    rels_dir = posixpath.dirname(part_name)
    source_dir = posixpath.dirname(rels_dir)
    if target.startswith("/"):
        return target.lstrip("/")
    return posixpath.normpath(posixpath.join(source_dir, target))


def _clean_relationships(part_name: str, data: bytes, removed: set[str]) -> bytes:
    root = ET.fromstring(data)
    changed = False
    for rel in list(root):
        target = rel.get("Target", "")
        rel_type = rel.get("Type", "")
        resolved = _relationship_target(part_name, target)
        if (
            resolved in removed
            or "comments" in rel_type.lower()
            or "people" in rel_type.lower()
            or "custom-properties" in rel_type.lower()
        ):
            root.remove(rel)
            changed = True
    return _xml_bytes(root, NS_REL) if changed else data


def _clean_content_types(data: bytes, removed: set[str]) -> bytes:
    root = ET.fromstring(data)
    changed = False
    removed_parts = {f"/{name}" for name in removed}
    for node in list(root):
        if node.get("PartName") in removed_parts:
            root.remove(node)
            changed = True
    return _xml_bytes(root, NS_CT) if changed else data


def normalize_docx(path: Path, author: str = AUTHOR) -> None:
    path = path.resolve()
    if not path.is_file():
        raise FileNotFoundError(path)

    with zipfile.ZipFile(path, "r") as zin:
        infos = zin.infolist()
        names = {info.filename for info in infos}
        removed = {name for name in names if COMMENT_PART_RE.match(name)}
        if "docProps/custom.xml" in names:
            removed.add("docProps/custom.xml")

        transformed: dict[str, bytes] = {}
        for info in infos:
            name = info.filename
            if name in removed:
                continue
            data = zin.read(name)
            if name == "docProps/core.xml":
                root = ET.fromstring(data)
                _set_child_text(root, f"{{{NS_DC}}}creator", author)
                _set_child_text(root, f"{{{NS_CP}}}lastModifiedBy", author)
                data = _xml_bytes(root)
            elif name == "docProps/app.xml":
                root = ET.fromstring(data)
                _set_child_text(root, f"{{{NS_EP}}}Company", "")
                _set_child_text(root, f"{{{NS_EP}}}Manager", "")
                data = _xml_bytes(root, NS_EP)
            elif name == "[Content_Types].xml":
                data = _clean_content_types(data, removed)
            elif name.endswith(".rels"):
                data = _clean_relationships(name, data, removed)
            elif name.startswith("word/") and name.endswith(".xml"):
                data = _strip_comment_markers(data)
            transformed[name] = data

    stat = path.stat()
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    os.close(fd)
    tmp_path = Path(tmp_name)
    try:
        with zipfile.ZipFile(tmp_path, "w") as zout:
            for info in infos:
                if info.filename in removed:
                    continue
                zout.writestr(info, transformed[info.filename])
        os.chmod(tmp_path, stat.st_mode)
        os.replace(tmp_path, path)
    finally:
        tmp_path.unlink(missing_ok=True)


def audit_docx(path: Path, author: str = AUTHOR) -> dict[str, object]:
    with zipfile.ZipFile(path, "r") as zf:
        names = zf.namelist()
        core = ET.fromstring(zf.read("docProps/core.xml"))
        app = ET.fromstring(zf.read("docProps/app.xml"))
        creator = core.findtext(f"{{{NS_DC}}}creator") or ""
        modified_by = core.findtext(f"{{{NS_CP}}}lastModifiedBy") or ""
        company = app.findtext(f"{{{NS_EP}}}Company") or ""
        manager = app.findtext(f"{{{NS_EP}}}Manager") or ""

        author_parts = [
            name
            for name in names
            if COMMENT_PART_RE.match(name) or name == "docProps/custom.xml"
        ]
        xml_payloads = {
            name: zf.read(name)
            for name in names
            if name.endswith((".xml", ".rels"))
        }
        comment_markers = [
            name
            for name, payload in xml_payloads.items()
            if b"commentRange" in payload or b"commentReference" in payload
        ]
        tracked_changes = [
            name
            for name, payload in xml_payloads.items()
            if any(pattern.search(payload) for pattern in TRACKED_CHANGE_PATTERNS)
        ]
        rsid_attributes = [
            name
            for name, payload in xml_payloads.items()
            if re.search(br"\bw:rsid[A-Za-z]*=", payload)
        ]

    passed = (
        creator == author
        and modified_by == author
        and not company
        and not manager
        and not author_parts
        and not comment_markers
        and not tracked_changes
        and not rsid_attributes
    )
    return {
        "file": str(path),
        "creator": creator,
        "lastModifiedBy": modified_by,
        "company": company,
        "manager": manager,
        "author_parts": author_parts,
        "comment_markers": comment_markers,
        "tracked_changes": tracked_changes,
        "rsid_attributes": rsid_attributes,
        "passed": passed,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--author", default=AUTHOR)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Audit metadata without modifying files",
    )
    args = parser.parse_args()

    reports = []
    for path in args.paths:
        if not args.check:
            normalize_docx(path, args.author)
        reports.append(audit_docx(path, args.author))
    print(json.dumps(reports, ensure_ascii=False, indent=2))
    return 0 if all(report["passed"] for report in reports) else 1


if __name__ == "__main__":
    raise SystemExit(main())
