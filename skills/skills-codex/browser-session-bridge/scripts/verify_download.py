#!/usr/bin/env python3
"""Verify browser-downloaded research artifacts without trusting extensions."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import zipfile
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path


class ExpectedFormat(str, Enum):
    ANY = "any"
    CSV = "csv"
    PDF = "pdf"
    XLSX = "xlsx"
    ZIP = "zip"


DEFAULT_MIN_BYTES: dict[ExpectedFormat, int] = {
    ExpectedFormat.ANY: 1,
    ExpectedFormat.CSV: 1,
    ExpectedFormat.PDF: 10_240,
    ExpectedFormat.XLSX: 100,
    ExpectedFormat.ZIP: 100,
}


@dataclass(frozen=True)
class VerificationResult:
    ok: bool
    path: str
    expected_format: str
    detected_format: str
    size_bytes: int
    sha256: str
    error: str | None


class VerificationError(ValueError):
    """Raised when a landed file fails an acceptance invariant."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def looks_like_html(prefix: bytes) -> bool:
    text = prefix.lstrip().lower()
    return text.startswith((b"<!doctype html", b"<html")) or b"<html" in text[:4096]


def verify_pdf(path: Path, prefix: bytes) -> str:
    if not prefix.startswith(b"%PDF-"):
        raise VerificationError("missing PDF magic bytes")
    with path.open("rb") as handle:
        tail_size = min(path.stat().st_size, 4096)
        handle.seek(-tail_size, 2)
        tail = handle.read()
    if b"%%EOF" not in tail:
        raise VerificationError("PDF EOF marker not found; download may be partial")
    return "pdf"


def verify_zip(path: Path, expect_xlsx: bool) -> str:
    try:
        with zipfile.ZipFile(path) as archive:
            bad_member = archive.testzip()
            if bad_member is not None:
                raise VerificationError(f"corrupt ZIP member: {bad_member}")
            names = set(archive.namelist())
    except zipfile.BadZipFile as exc:
        raise VerificationError("invalid ZIP container") from exc
    if expect_xlsx:
        required = {"[Content_Types].xml", "xl/workbook.xml"}
        missing = sorted(required - names)
        if missing:
            raise VerificationError(f"XLSX container missing: {', '.join(missing)}")
        return "xlsx"
    return "zip"


def decode_text(data: bytes) -> str:
    for encoding in ("utf-8-sig", "gb18030"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise VerificationError("CSV preview is neither UTF-8 nor GB18030 text")


def verify_csv(prefix: bytes) -> str:
    if b"\x00" in prefix:
        raise VerificationError("CSV preview contains NUL bytes")
    text = decode_text(prefix)
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        raise VerificationError("CSV contains no non-empty rows")
    try:
        csv.Sniffer().sniff("\n".join(lines[:20]), delimiters=",\t;")
    except csv.Error as exc:
        if len(lines) == 1:
            raise VerificationError("CSV has no detectable delimiter or data row") from exc
    return "csv"


def verify(path: Path, expected: ExpectedFormat, min_bytes: int) -> VerificationResult:
    resolved = path.expanduser().resolve()
    size = 0
    digest = ""
    detected = "unknown"
    try:
        if not resolved.is_file():
            raise VerificationError("file does not exist or is not a regular file")
        size = resolved.stat().st_size
        if size < min_bytes:
            raise VerificationError(f"file is {size} bytes; minimum is {min_bytes}")
        with resolved.open("rb") as handle:
            prefix = handle.read(65_536)
        if looks_like_html(prefix):
            raise VerificationError("HTML response masquerades as a download")
        if expected is ExpectedFormat.PDF:
            detected = verify_pdf(resolved, prefix)
        elif expected is ExpectedFormat.XLSX:
            detected = verify_zip(resolved, expect_xlsx=True)
        elif expected is ExpectedFormat.ZIP:
            detected = verify_zip(resolved, expect_xlsx=False)
        elif expected is ExpectedFormat.CSV:
            detected = verify_csv(prefix)
        else:
            detected = "binary_or_text"
        digest = sha256_file(resolved)
        return VerificationResult(True, str(resolved), expected.value, detected, size, digest, None)
    except (OSError, VerificationError) as exc:
        return VerificationResult(False, str(resolved), expected.value, detected, size, digest, str(exc))


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="landed file to verify")
    parser.add_argument(
        "--expect",
        choices=[item.value for item in ExpectedFormat],
        default=ExpectedFormat.ANY.value,
        help="expected content format",
    )
    parser.add_argument("--min-bytes", type=int, help="minimum accepted size")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    expected = ExpectedFormat(args.expect)
    min_bytes = args.min_bytes if args.min_bytes is not None else DEFAULT_MIN_BYTES[expected]
    if min_bytes < 0:
        print(json.dumps({"ok": False, "error": "--min-bytes must be non-negative"}))
        return 2
    result = verify(args.path, expected, min_bytes)
    print(json.dumps(asdict(result), ensure_ascii=False, sort_keys=True))
    return 0 if result.ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
