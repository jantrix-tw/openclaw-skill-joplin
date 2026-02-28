"""
get_note.py — Retrieve a Joplin note by ID.

Usage:
    python get_note.py --id <note_id>

Note body is truncated at 8000 chars and wrapped in security delimiters.
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
import joplin_client as jc


def main():
    parser = argparse.ArgumentParser(description="Get a Joplin note by ID")
    parser.add_argument("--id", required=True, help="Note ID")
    args = parser.parse_args()

    data = jc.get_note_with_wrap(args.id)
    jc.ok(data)


if __name__ == "__main__":
    main()
