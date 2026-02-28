"""
search_notes.py — Search Joplin notes by keyword.

Usage:
    python search_notes.py --query "meeting" [--limit 20]
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
import joplin_client as jc


def main():
    parser = argparse.ArgumentParser(description="Search Joplin notes")
    parser.add_argument("--query", required=True, help="Search query string")
    parser.add_argument("--limit", type=int, default=20, help="Maximum results (default: 20)")
    args = parser.parse_args()

    if args.limit < 1 or args.limit > 100:
        jc.die("--limit must be between 1 and 100.")

    data = jc.joplin_get(
        "/search",
        params={
            "query": args.query,
            "limit": args.limit,
            "fields": "id,title,parent_id,updated_time",
        },
    )
    # Joplin returns {"items": [...], "has_more": bool}
    items = data.get("items", data if isinstance(data, list) else [])
    jc.ok({"results": items, "count": len(items)})


if __name__ == "__main__":
    main()
