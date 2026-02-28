"""
list_notebooks.py — List all Joplin notebooks (folders).

Usage:
    python list_notebooks.py [--limit 100]
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
import joplin_client as jc


def main():
    parser = argparse.ArgumentParser(description="List all Joplin notebooks")
    parser.add_argument("--limit", type=int, default=100, help="Maximum notebooks to return (default: 100)")
    args = parser.parse_args()

    if args.limit < 1 or args.limit > 100:
        jc.die("--limit must be between 1 and 100.")

    data = jc.joplin_get(
        "/folders",
        params={"fields": "id,title,parent_id", "limit": args.limit},
    )
    items = data.get("items", data if isinstance(data, list) else [])
    jc.ok({"notebooks": items, "count": len(items)})


if __name__ == "__main__":
    main()
