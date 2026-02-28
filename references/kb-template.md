# Knowledge Base Note Template

Every KB note created by the `save_kb_*` scripts uses this body structure.

## Template

```
---
kb_source: <url or filepath or "manual">
kb_type: webpage|image|video|text|file
kb_captured: <YYYY-MM-DD>
---

## Summary
<1-3 sentences describing what this is>

## Content
<full text, embedded image markdown, or path reference>
```

---

## Field Definitions

| Field        | Description                                            |
|--------------|--------------------------------------------------------|
| `kb_source`  | Origin URL, absolute file path, or literal `manual`    |
| `kb_type`    | One of: `webpage`, `image`, `video`, `text`, `file`   |
| `kb_captured`| ISO 8601 date the item was saved (`YYYY-MM-DD`)        |

---

## Content Conventions by Type

### `webpage`
Content is the full page text converted to Markdown via `html2text`.
Truncated at 50 000 characters.

### `image`
Content is a Joplin resource embed:
```markdown
![Note title](:/{resource_id})
```

### `video` / `file` (≤ 50 MB)
Content is a Joplin resource link:
```markdown
[filename.ext](:/{resource_id})
```

### `video` / `file` (> 50 MB)
Content records the local path only:
```markdown
**Large file — stored as path reference only**

Path: `/absolute/path/to/file.mp4`
Size: 123,456,789 bytes

> Note: file exceeds 50 MB upload limit.
```

### `text`
Content is the full plain-text body provided by the user or agent.

---

## Parsing in search_kb.py

The `search_kb.py` script parses KB notes using:
1. Regex to extract the `--- ... ---` frontmatter block.
2. Regex to extract the content of `## Summary`.

Notes that do not match this format will return empty strings for those fields.
