"""
list_notes_in_notebook.py — List notes inside a specific Joplin notebook.

Usage:
    python list_notes_in_notebook.py --notebook-id <folder_id> [--limit 50]
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
import joplin_client as jc


def main():
    parser = argparse.ArgumentParser(description="List notes in a Joplin notebook")
    parser.add_argument("--notebook-id", required=True, help="Notebook (folder) ID")
    parser.add_argument("--limit", type=int, default=50, help="Maximum notes to return (default: 50)")
    args = parser.parse_args()

    notebook_id = jc.validate_id(args.notebook_id, "notebook_id")

    if args.limit < 1 or args.limit > 100:
        jc.die("--limit must be between 1 and 100.")

    data = jc.joplin_get(
        f"/folders/{notebook_id}/notes",
        params={"fields": "id,title,updated_time", "limit": args.limit},
    )
    items = data.get("items", data if isinstance(data, list) else [])
    jc.ok({"notes": items, "count": len(items), "notebook_id": notebook_id})


if __name__ == "__main__":
    main()
