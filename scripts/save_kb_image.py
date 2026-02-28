"""
save_kb_image.py — Upload an image file and save it as a KB note.

Usage:
    python save_kb_image.py --filepath /path/to/image.png --title "My Image" \
        --summary "Description" --notebook-id <folder_id> [--tags "tag1,tag2"]

Supported extensions: jpg, jpeg, png, gif, webp, svg
Size limit: 50 MB
"""

import argparse
import mimetypes
import sys
import os
from datetime import date

sys.path.insert(0, os.path.dirname(__file__))
import joplin_client as jc

# Allowed image extensions (lowercase)
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp", "svg"}

# 50 MB in bytes
MAX_SIZE_BYTES = 50 * 1024 * 1024


def main():
    parser = argparse.ArgumentParser(description="Save an image as a KB note")
    parser.add_argument("--filepath", required=True, help="Path to image file")
    parser.add_argument("--title", required=True, help="Note title")
    parser.add_argument("--summary", required=True, help="1-3 sentence summary")
    parser.add_argument("--notebook-id", required=True, help="Target notebook ID")
    parser.add_argument("--tags", default="", help="Comma-separated tag names (optional)")
    args = parser.parse_args()

    notebook_id = jc.validate_id(args.notebook_id, "notebook_id")

    # --- Path traversal prevention (PATCH 3) ---
    real_path = os.path.realpath(args.filepath)
    safe_base = os.path.expanduser("~")
    if not (real_path == safe_base or real_path.startswith(safe_base + os.sep)):
        jc.die("File path must be within the home directory.")
    if not os.path.exists(real_path):
        jc.die("File not found at the specified path.")
    if not os.path.isfile(real_path):
        jc.die("Specified path is not a file.")

    # --- Extension validation ---
    # Use real_path (canonicalized) for all post-check operations to prevent
    # symlink-swap TOCTOU between realpath() check and actual file access.
    ext = os.path.splitext(real_path)[1].lstrip(".").lower()
    if ext not in ALLOWED_EXTENSIONS:
        jc.die(f"Unsupported image extension. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}")

    # --- Size check ---
    file_size = os.path.getsize(real_path)
    if file_size > MAX_SIZE_BYTES:
        jc.die("Image file exceeds the 50 MB limit.")

    # --- Upload as Joplin resource ---
    mime_type = mimetypes.guess_type(real_path)[0] or "application/octet-stream"
    filename = os.path.basename(real_path)

    with open(real_path, "rb") as fh:
        resource_data = jc.joplin_post(
            "/resources",
            data={"title": args.title},
            files={"data": (filename, fh, mime_type)},
        )

    resource_id = resource_data.get("id")
    if not resource_id:
        jc.die("Resource upload did not return an ID.")
    resource_id = jc.validate_id(resource_id, "resource_id")

    today = date.today().strftime("%Y-%m-%d")
    # PATCH 5: sanitize filepath to prevent newline injection in frontmatter
    safe_filepath = args.filepath.replace('\n', ' ').replace('\r', ' ')
    kb_body = (
        f"---\n"
        f"kb_source: {safe_filepath}\n"
        f"kb_type: image\n"
        f"kb_captured: {today}\n"
        f"---\n\n"
        f"## Summary\n{args.summary}\n\n"
        f"## Content\n![{args.title}](:/{resource_id})"
    )

    note = jc.joplin_post("/notes", data={
        "title": args.title,
        "body": kb_body,
        "parent_id": notebook_id,
    })
    note_id = note.get("id")

    if args.tags:
        from save_kb_text import apply_tags
        apply_tags(note_id, args.tags)

    jc.ok({
        "id": note_id,
        "title": args.title,
        "kb_type": "image",
        "resource_id": resource_id,
        "file_size": file_size,
    })


if __name__ == "__main__":
    main()
