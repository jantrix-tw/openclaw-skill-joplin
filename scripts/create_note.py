"""
create_note.py — Create a new Joplin note.

Usage:
    python create_note.py --title "My Note" --body "Content here" --notebook-id <folder_id>
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
import joplin_client as jc


def main():
    parser = argparse.ArgumentParser(description="Create a new Joplin note")
    parser.add_argument("--title", required=True, help="Note title")
    parser.add_argument("--body", required=True, help="Note body (Markdown)")
    parser.add_argument("--notebook-id", required=True, help="Target notebook (folder) ID")
    args = parser.parse_args()

    # Validate the notebook ID before using it in any request
    notebook_id = jc.validate_id(args.notebook_id, "notebook_id")

    data = jc.joplin_post("/notes", data={
        "title": args.title,
        "body": args.body,
        "parent_id": notebook_id,
    })
    jc.ok({"id": data.get("id"), "title": data.get("title"), "parent_id": data.get("parent_id")})


if __name__ == "__main__":
    main()
