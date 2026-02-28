"""
save_kb_file.py — Save a non-image file (PDF, ZIP, MP4, etc.) as a KB note.

Usage:
    python save_kb_file.py --filepath /path/to/doc.pdf --title "My Doc" \
        --summary "Description" --notebook-id <folder_id> [--tags "tag1,tag2"]

Under 50 MB: file is uploaded as a Joplin resource attachment.
Over 50 MB:  only the file path is stored (no upload).
"""

import argparse
import mimetypes
import sys
import os
from datetime import date

sys.path.insert(0, os.path.dirname(__file__))
import joplin_client as jc

# Extensions treated as video type
VIDEO_EXTENSIONS = {"mp4", "mkv", "avi", "mov", "webm", "m4v", "flv"}

# 50 MB in bytes
MAX_SIZE_BYTES = 50 * 1024 * 1024


def _detect_kb_type(ext: str) -> str:
    """Map a file extension to a KB type string."""
    if ext in VIDEO_EXTENSIONS:
        return "video"
    return "file"


def main():
    parser = argparse.ArgumentParser(description="Save a file as a KB note")
    parser.add_argument("--filepath", required=True, help="Path to the file")
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

    # Use real_path (canonicalized) for all post-check operations to prevent
    # symlink-swap TOCTOU between realpath() check and actual file access.
    ext = os.path.splitext(real_path)[1].lstrip(".").lower()
    kb_type = _detect_kb_type(ext)
    file_size = os.path.getsize(real_path)
    today = date.today().strftime("%Y-%m-%d")
    filename = os.path.basename(real_path)

    # PATCH 5: sanitize filepath to prevent newline injection in frontmatter
    # and note body (hoisted before the if/else so both branches can use it).
    safe_filepath = args.filepath.replace('\n', ' ').replace('\r', ' ')

    if file_size <= MAX_SIZE_BYTES:
        # Upload as a resource attachment
        mime_type = mimetypes.guess_type(real_path)[0] or "application/octet-stream"
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

        content_section = f"[{filename}](:/{resource_id})"
        result_extra = {"resource_id": resource_id}
    else:
        # Too large to upload — store as a path reference only
        content_section = (
            f"**Large file — stored as path reference only**\n\n"
            f"Path: `{safe_filepath}`\n"
            f"Size: {file_size:,} bytes\n\n"
            f"> Note: file exceeds 50 MB upload limit."
        )
        result_extra = {"path_reference_only": True}

    # safe_filepath already defined above (hoisted from PATCH 5)
    kb_body = (
        f"---\n"
        f"kb_source: {safe_filepath}\n"
        f"kb_type: {kb_type}\n"
        f"kb_captured: {today}\n"
        f"---\n\n"
        f"## Summary\n{args.summary}\n\n"
        f"## Content\n{content_section}"
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

    jc.ok({"id": note_id, "title": args.title, "kb_type": kb_type, "file_size": file_size, **result_extra})


if __name__ == "__main__":
    main()
