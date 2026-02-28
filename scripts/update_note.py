"""
update_note.py — Update the body (and optionally title) of a Joplin note.

Usage:
    python update_note.py --id <note_id> --body "New content" [--title "New title"]
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
import joplin_client as jc


def main():
    parser = argparse.ArgumentParser(description="Update a Joplin note")
    parser.add_argument("--id", required=True, help="Note ID")
    parser.add_argument("--body", required=True, help="New note body (Markdown)")
    parser.add_argument("--title", default=None, help="New note title (optional)")
    args = parser.parse_args()

    note_id = jc.validate_id(args.id, "note_id")

    payload: dict = {"body": args.body}
    if args.title is not None:
        payload["title"] = args.title

    data = jc.joplin_put(f"/notes/{note_id}", data=payload)
    jc.ok({"id": data.get("id", note_id), "updated": True})


if __name__ == "__main__":
    main()
