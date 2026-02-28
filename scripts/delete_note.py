"""
delete_note.py — Delete a Joplin note by ID.

Usage:
    python delete_note.py --id <note_id>
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
import joplin_client as jc


def main():
    parser = argparse.ArgumentParser(description="Delete a Joplin note")
    parser.add_argument("--id", required=True, help="Note ID")
    args = parser.parse_args()

    note_id = jc.validate_id(args.id, "note_id")
    jc.joplin_delete(f"/notes/{note_id}")
    jc.ok({"id": note_id, "deleted": True})


if __name__ == "__main__":
    main()
