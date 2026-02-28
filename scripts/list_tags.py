"""
list_tags.py — List all tags in Joplin.

Usage:
    python list_tags.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
import joplin_client as jc


def main():
    data = jc.joplin_get(
        "/tags",
        params={"fields": "id,title", "limit": 100},
    )
    items = data.get("items", data if isinstance(data, list) else [])
    jc.ok({"tags": items, "count": len(items)})


if __name__ == "__main__":
    main()
