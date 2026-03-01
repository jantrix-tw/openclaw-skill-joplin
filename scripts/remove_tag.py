"""
remove_tag.py — Remove a tag from a Joplin note.

Usage:
    # Remove by tag name (recommended — resolves ID automatically):
    python remove_tag.py --note-id <note_id> --tag <tag_name>

    # Remove by tag ID (fallback):
    python remove_tag.py --note-id <note_id> --tag-id <tag_id>

One of --tag or --tag-id is required.
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
import joplin_client as jc


def _resolve_tag_id_by_name(tag_name: str) -> str:
    """Look up a tag ID by its title.  Pages through /tags until found.

    Exits with an error if no tag with that name exists.
    """
    page = 1
    while True:
        result = jc.joplin_get("/tags", params={"page": page, "limit": 100, "fields": "id,title"})
        # Joplin returns {"items": [...], "has_more": bool} for list endpoints
        items = result.get("items", [])
        if not items and isinstance(result, list):
            # Fallback: some Joplin versions return a plain list
            items = result
        for tag in items:
            if tag.get("title", "").lower() == tag_name.lower():
                return jc.validate_id(tag["id"], "tag_id")
        if not result.get("has_more", False):
            break
        page += 1
    jc.die(f"Tag not found: no tag named '{tag_name}' exists in Joplin.")


def main():
    parser = argparse.ArgumentParser(description="Remove a tag from a Joplin note")
    parser.add_argument("--note-id", required=True, help="Note ID")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--tag", help="Tag name (resolved to ID automatically)")
    group.add_argument("--tag-id", help="Tag ID (direct lookup, skips name resolution)")
    args = parser.parse_args()

    note_id = jc.validate_id(args.note_id, "note_id")

    if args.tag_id:
        tag_id = jc.validate_id(args.tag_id, "tag_id")
    else:
        tag_id = _resolve_tag_id_by_name(args.tag)

    jc.joplin_delete(f"/tags/{tag_id}/notes/{note_id}")
    jc.ok({"note_id": note_id, "tag_id": tag_id, "removed": True})


if __name__ == "__main__":
    main()
