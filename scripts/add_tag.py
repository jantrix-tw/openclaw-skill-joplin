"""
add_tag.py — Add a tag to a Joplin note.

Usage:
    python add_tag.py --note-id <note_id> --tag "tag name"

If the tag does not exist it is created automatically, then linked to the note.
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
import joplin_client as jc


def _find_or_create_tag(tag_name: str) -> str:
    """Return the tag ID for *tag_name*, creating it if it does not exist."""
    data = jc.joplin_get("/tags", params={"fields": "id,title", "limit": 100})
    items = data.get("items", data if isinstance(data, list) else [])

    # Case-insensitive search for existing tag
    normalized = tag_name.strip().lower()
    for tag in items:
        if tag.get("title", "").lower() == normalized:
            return tag["id"]

    # Tag not found — create it
    created = jc.joplin_post("/tags", data={"title": tag_name.strip()})
    return created["id"]


def main():
    parser = argparse.ArgumentParser(description="Add a tag to a Joplin note")
    parser.add_argument("--note-id", required=True, help="Note ID")
    parser.add_argument("--tag", required=True, help="Tag name to add")
    args = parser.parse_args()

    note_id = jc.validate_id(args.note_id, "note_id")

    tag_id = _find_or_create_tag(args.tag)
    tag_id = jc.validate_id(tag_id, "tag_id")

    # Link the tag to the note
    jc.joplin_post(f"/tags/{tag_id}/notes", data={"id": note_id})
    jc.ok({"note_id": note_id, "tag_id": tag_id, "tag": args.tag.strip(), "linked": True})


if __name__ == "__main__":
    main()
