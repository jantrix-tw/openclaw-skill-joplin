"""
save_kb_text.py — Save a plain-text knowledge base note in Joplin.

Usage:
    python save_kb_text.py --title "My Note" --body "Full content" \
        --summary "1-3 sentence summary" --notebook-id <folder_id> \
        [--tags "tag1,tag2"]
"""

import argparse
import sys
import os
from datetime import date

sys.path.insert(0, os.path.dirname(__file__))
import joplin_client as jc


def build_kb_body(summary: str, content: str, kb_type: str = "text", kb_source: str = "manual") -> str:
    """Assemble a KB note body using the standard frontmatter template."""
    today = date.today().strftime("%Y-%m-%d")
    return (
        f"---\n"
        f"kb_source: {kb_source}\n"
        f"kb_type: {kb_type}\n"
        f"kb_captured: {today}\n"
        f"---\n\n"
        f"## Summary\n{summary}\n\n"
        f"## Content\n{content}"
    )


def apply_tags(note_id: str, tags_csv: str) -> None:
    """Parse a comma-separated tag string and add each tag to the note."""
    tags = [t.strip() for t in tags_csv.split(",") if t.strip()]
    for tag_name in tags:
        # Reuse the find-or-create logic inline to avoid subprocess overhead
        data = jc.joplin_get("/tags", params={"fields": "id,title", "limit": 100})
        items = data.get("items", data if isinstance(data, list) else [])
        normalized = tag_name.lower()
        tag_id = None
        for tag in items:
            if tag.get("title", "").lower() == normalized:
                tag_id = tag["id"]
                break
        if tag_id is None:
            created = jc.joplin_post("/tags", data={"title": tag_name})
            tag_id = created["id"]
        tag_id = jc.validate_id(tag_id, "tag_id")
        jc.joplin_post(f"/tags/{tag_id}/notes", data={"id": note_id})


def main():
    parser = argparse.ArgumentParser(description="Save a text knowledge base note")
    parser.add_argument("--title", required=True, help="Note title")
    parser.add_argument("--body", required=True, help="Full content text")
    parser.add_argument("--summary", required=True, help="1-3 sentence summary")
    parser.add_argument("--notebook-id", required=True, help="Target notebook ID")
    parser.add_argument("--tags", default="", help="Comma-separated tag names (optional)")
    args = parser.parse_args()

    notebook_id = jc.validate_id(args.notebook_id, "notebook_id")
    kb_body = build_kb_body(summary=args.summary, content=args.body, kb_type="text", kb_source="manual")

    note = jc.joplin_post("/notes", data={
        "title": args.title,
        "body": kb_body,
        "parent_id": notebook_id,
    })
    note_id = note.get("id")

    if args.tags:
        apply_tags(note_id, args.tags)

    jc.ok({"id": note_id, "title": args.title, "kb_type": "text"})


if __name__ == "__main__":
    main()
