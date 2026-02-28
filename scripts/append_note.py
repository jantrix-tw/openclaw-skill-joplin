"""
append_note.py — Append text to the end of an existing Joplin note.

Usage:
    python append_note.py --id <note_id> --text "Additional content"

Reads the current body, appends text with a blank-line separator, then writes back.
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
import joplin_client as jc


def main():
    parser = argparse.ArgumentParser(description="Append text to a Joplin note")
    parser.add_argument("--id", required=True, help="Note ID")
    parser.add_argument("--text", required=True, help="Text to append")
    args = parser.parse_args()

    note_id = jc.validate_id(args.id, "note_id")

    # Fetch the raw body (without wrapping) so we can append to it cleanly
    current = jc.joplin_get(
        f"/notes/{note_id}",
        params={"fields": "id,title,body"},
    )
    existing_body = current.get("body", "")

    # Append with a blank-line separator for Markdown readability
    new_body = existing_body.rstrip("\n") + "\n\n" + args.text

    jc.joplin_put(f"/notes/{note_id}", data={"body": new_body})
    jc.ok({"id": note_id, "appended": True, "new_length": len(new_body)})


if __name__ == "__main__":
    main()
