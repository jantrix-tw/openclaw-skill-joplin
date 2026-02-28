# Joplin REST API Reference

Joplin exposes a local REST API via the Web Clipper plugin.

## Base URL

```
http://localhost:41184
```

## Authentication

Append `?token={JOPLIN_TOKEN}` to every request.
The token is read from the `JOPLIN_TOKEN` environment variable — never hardcoded.

## Pagination

Joplin paginates responses with `page` and `limit` query params.
Responses include `{ "items": [...], "has_more": bool }`.

---

## Notes

### Search notes
```
GET /search?query=X&limit=N&fields=id,title,parent_id,updated_time
```

### Create note
```
POST /notes
Body (JSON): { "title": "...", "body": "...", "parent_id": "<folder_id>" }
```

### Get note
```
GET /notes/{id}?fields=id,title,body,parent_id,created_time,updated_time
```

### Update note
```
PUT /notes/{id}
Body (JSON): { "body": "..." }  or  { "title": "...", "body": "..." }
```

### Delete note
```
DELETE /notes/{id}
Returns: 204 No Content
```

---

## Folders (Notebooks)

### List all folders
```
GET /folders?fields=id,title,parent_id&limit=N
```

### List notes in a folder
```
GET /folders/{id}/notes?fields=id,title,updated_time&limit=N
```

---

## Resources (File Attachments)

### Upload a resource
```
POST /resources
Content-Type: multipart/form-data
Fields: data=<file>, title=<string>
```
Response includes `{ "id": "<resource_id>" }`.

### Embed an uploaded image in a note body
```markdown
![Alt text](:/{resource_id})
```

### Embed a file attachment link
```markdown
[filename](:/{resource_id})
```

---

## Tags

### List all tags
```
GET /tags?fields=id,title&limit=100
```

### Create a tag
```
POST /tags
Body (JSON): { "title": "tag name" }
```

### Link a tag to a note
```
POST /tags/{tag_id}/notes
Body (JSON): { "id": "<note_id>" }
```

### Remove a tag from a note
```
DELETE /tags/{tag_id}/notes/{note_id}
Returns: 204 No Content
```

---

## Field Filtering

Use `?fields=id,title,...` to limit response payload size.
Available note fields: `id`, `title`, `body`, `parent_id`, `created_time`, `updated_time`.

---

## Useful Tips

- **Sort order**: Joplin does not expose a sort parameter in v1 search; results are ranked by relevance.
- **Folder hierarchy**: `parent_id` is empty string `""` for root-level notebooks.
- **Markdown body**: Joplin stores note bodies as Markdown; use standard Markdown syntax.
- **Resource embedding**: Resources uploaded via `/resources` are referenced in note bodies using `:/{id}` URIs.
