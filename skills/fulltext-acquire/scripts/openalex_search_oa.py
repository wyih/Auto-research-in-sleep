#!/usr/bin/env python3
"""Search OpenAlex for works; prefer open-access PDF URLs.

No API key required for light use. Polite pool: set OPENALEX_MAILTO.
Prints JSON to stdout. Does not download PDFs (see download_open_pdf.py).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request


def main() -> int:
    p = argparse.ArgumentParser(description="OpenAlex search with OA PDF URLs")
    p.add_argument("query", help="search string")
    p.add_argument("--per-page", type=int, default=10)
    p.add_argument("--oa-only", action="store_true", help="filter is_oa:true")
    p.add_argument("--year-from", type=int, default=None)
    p.add_argument("--year-to", type=int, default=None)
    args = p.parse_args()

    filters = []
    if args.oa_only:
        filters.append("is_oa:true")
    if args.year_from is not None and args.year_to is not None:
        filters.append(f"from_publication_date:{args.year_from}-01-01,to_publication_date:{args.year_to}-12-31")
    elif args.year_from is not None:
        filters.append(f"from_publication_date:{args.year_from}-01-01")

    params = {
        "search": args.query,
        "per_page": str(max(1, min(args.per_page, 50))),
    }
    if filters:
        params["filter"] = ",".join(filters)

    url = "https://api.openalex.org/works?" + urllib.parse.urlencode(params)
    mailto = os.environ.get("OPENALEX_MAILTO", "").strip()
    headers = {"User-Agent": f"fulltext-acquire/1.0 (mailto:{mailto or 'research@localhost'})"}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    out = []
    for w in data.get("results") or []:
        oa = w.get("open_access") or {}
        primary = w.get("primary_location") or {}
        pdf = (
            oa.get("oa_url")
            or primary.get("pdf_url")
            or (primary.get("landing_page_url") if primary.get("is_oa") else None)
        )
        out.append(
            {
                "id": w.get("id"),
                "title": w.get("display_name"),
                "year": w.get("publication_year"),
                "doi": w.get("doi"),
                "cited_by": w.get("cited_by_count"),
                "oa_url": oa.get("oa_url"),
                "pdf_url": pdf,
                "is_oa": oa.get("is_oa"),
                "venue": ((w.get("primary_location") or {}).get("source") or {}).get("display_name"),
            }
        )

    print(
        json.dumps(
            {
                "query": args.query,
                "count_total": (data.get("meta") or {}).get("count"),
                "n_returned": len(out),
                "results": out,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        raise SystemExit(1)
