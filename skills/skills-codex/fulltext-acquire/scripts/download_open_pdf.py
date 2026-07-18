#!/usr/bin/env python3
"""Download one open PDF URL to literature/fulltext/open/ with size + sha256 checks.

Acceptance for open channel: HTTP GET returns PDF magic and size > 10KB.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--url", required=True)
    p.add_argument("--out-dir", default="literature/fulltext/open")
    p.add_argument("--paper-id", default="paper")
    p.add_argument("--min-bytes", type=int, default=10_000)
    args = p.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", args.paper_id)[:80]
    dest = out_dir / f"{safe}.pdf"

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) fulltext-acquire/1.0",
        "Accept": "application/pdf,*/*",
    }
    req = urllib.request.Request(args.url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = resp.read()
            final_url = resp.geturl()
            ctype = resp.headers.get("Content-Type", "")
    except urllib.error.HTTPError as e:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "http_error",
                    "status": e.code,
                    "url": args.url,
                    "reason": str(e.reason),
                }
            )
        )
        return 1
    except urllib.error.URLError as e:
        print(json.dumps({"ok": False, "error": "url_error", "url": args.url, "reason": str(e.reason)}))
        return 1

    if len(data) < args.min_bytes:
        print(json.dumps({"ok": False, "error": "too_small", "bytes": len(data), "url": final_url}))
        return 2
    if not data.startswith(b"%PDF") and "pdf" not in ctype.lower():
        # allow if magic is PDF even when content-type wrong
        if not data.startswith(b"%PDF"):
            print(
                json.dumps(
                    {
                        "ok": False,
                        "error": "not_pdf",
                        "content_type": ctype,
                        "bytes": len(data),
                        "url": final_url,
                        "head": data[:20].decode("latin-1", errors="replace"),
                    }
                )
            )
            return 3

    dest.write_bytes(data)
    h = hashlib.sha256(data).hexdigest()
    rec = {
        "ok": True,
        "paper_id": args.paper_id,
        "path": str(dest.resolve()),
        "bytes": len(data),
        "sha256": h,
        "source_url": args.url,
        "final_url": final_url,
        "acquired_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "fulltext_status": "open",
        "channel": "open",
    }
    print(json.dumps(rec, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
