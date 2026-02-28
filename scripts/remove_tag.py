"""
remove_tag.py — Remove a tag from a Joplin note.

Usage:
    python remove_tag.py --note-id <note_id> --tag-id <tag_id>
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
import joplin_client as jc


def main():
    parser = argparse.ArgumentParser(description="Remove a tag from a Joplin note")
    parser.add_argument("--note-id", required=True, help="Note ID")
    parser.add_argument("--tag-id", required=True, help="Tag ID to remove")
    args = parser.parse_args()

    note_id = jc.validate_id(args.note_id, "note_id")
    tag_id = jc.validate_id(args.tag_id, "tag_id")

    jc.joplin_delete(f"/tags/{tag_id}/notes/{note_id}")
    jc.ok({"note_id": note_id, "tag_id": tag_id, "removed": True})


if __name__ == "__main__":
    main()
