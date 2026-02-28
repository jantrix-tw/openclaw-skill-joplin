"""
search_kb.py — Search the Joplin knowledge base and return structured results.

Usage:
    python search_kb.py --query "machine learning" [--limit 10]

Parses each result's KB frontmatter and ## Summary section to return
structured KB metadata alongside the usual note fields.
"""

import argparse
import re
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
import joplin_client as jc


def _parse_kb_frontmatter(body: str) -> dict:
    """Extract kb_source, kb_type, kb_captured from the YAML-like frontmatter."""
    meta: dict = {}
    # Match the --- ... --- block at the start of the note
    match = re.match(r'^---\n(.*?)\n---', body, re.DOTALL)
    if not match:
        return meta
    for line in match.group(1).splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip()
    return meta


def _extract_summary(body: str) -> str:
    """Extract content under the ## Summary heading."""
    match = re.search(r'##\s+Summary\s*\n(.*?)(?:\n##|\Z)', body, re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""


def main():
    parser = argparse.ArgumentParser(description="Search Joplin KB notes")
    parser.add_argument("--query", required=True, help="Search query")
    parser.add_argument("--limit", type=int, default=10, help="Maximum results (default: 10)")
    args = parser.parse_args()

    if args.limit < 1 or args.limit > 100:
        jc.die("--limit must be between 1 and 100.")

    search_data = jc.joplin_get(
        "/search",
        params={
            "query": args.query,
            "limit": args.limit,
            "fields": "id,title,parent_id,updated_time",
        },
    )
    items = search_data.get("items", search_data if isinstance(search_data, list) else [])

    results = []
    for item in items:
        note_id = jc.validate_id(item.get("id", ""), "note_id")
        # Fetch full body for parsing
        full_note = jc.joplin_get(
            f"/notes/{note_id}",
            params={"fields": "id,title,body,updated_time"},
        )
        body = full_note.get("body", "")
        meta = _parse_kb_frontmatter(body)
        summary = _extract_summary(body)
        # PATCH 4: truncate and wrap summary/kb_source to limit injection surface
        safe_summary = summary[:500]
        safe_kb_source = meta.get("kb_source", "")[:200]
        # FIX 3: kb_type was previously returned raw; truncate and delimit for consistency
        safe_kb_type = meta.get("kb_type", "")[:50]
        results.append({
            "id": full_note.get("id"),
            "title": full_note.get("title"),
            "summary": f"--- FIELD START ---\n{safe_summary}\n--- FIELD END ---",
            "kb_type": f"--- FIELD START ---\n{safe_kb_type}\n--- FIELD END ---",
            "kb_source": f"--- FIELD START ---\n{safe_kb_source}\n--- FIELD END ---",
            "updated_time": full_note.get("updated_time"),
        })

    jc.ok({"results": results, "count": len(results)})


if __name__ == "__main__":
    main()
