# Error Handling Reference

All scripts in this skill print JSON to stdout only and exit with code 0 (success) or 1 (error).

## Output Contract

### Success
```json
{"status": "ok", "data": { ... }}
```

### Error
```json
{"status": "error", "error": "Human-readable message.", "code": 404}
```
`code` is omitted when there is no meaningful HTTP status to report.

---

## Standard Error Cases

| Scenario                        | Error message                                                                  | HTTP code |
|---------------------------------|--------------------------------------------------------------------------------|-----------|
| Joplin not running              | `Joplin not reachable. Ensure Joplin is running with Web Clipper enabled.`     | —         |
| Invalid token                   | `Invalid JOPLIN_TOKEN.`                                                        | 401       |
| Note / resource not found       | `Resource not found.`                                                          | 404       |
| Other HTTP error                | `Joplin API error (HTTP {status}).`                                            | varies    |
| Token env var not set           | `JOPLIN_TOKEN environment variable is not set.`                                | —         |
| Invalid ID characters           | `Invalid {name}: must contain only alphanumeric characters, dashes, or underscores.` | —   |
| URL scheme not http/https       | `Only http:// and https:// URLs are allowed.`                                  | —         |
| Private IP blocked (SSRF)       | `Requests to private or loopback addresses are not allowed.`                   | —         |
| Image extension not allowed     | `Unsupported image extension. Allowed: gif, jpeg, jpg, png, svg, webp`         | —         |
| File exceeds 50 MB (image)      | `Image file exceeds the 50 MB limit.`                                          | —         |
| File not found                  | `File not found at the specified path.`                                        | —         |
| Joplin returns non-JSON         | `Joplin returned non-JSON response.`                                           | —         |

---

## Security Constraints

1. **Token never in output**: `load_token()` reads from `os.environ` and the value is never printed or logged.
2. **ID validation**: All `note_id`, `folder_id`, `tag_id`, `resource_id` values are validated against `^[a-zA-Z0-9_-]+$` before being interpolated into URL paths.
3. **JSON body only**: POST and PUT requests pass data via `requests`' `json=` parameter, not string-concatenation.
4. **SSRF prevention**: `save_kb_url.py` resolves the hostname and checks against private CIDR ranges before fetching.
5. **Content delimiters**: Note bodies returned to the agent are wrapped in `--- NOTE CONTENT START ---` / `--- NOTE CONTENT END ---` so agents can distinguish user data from system instructions.
6. **No verbatim echo**: Error messages describe the problem category, never repeat raw user input.

---

## Body Truncation

If a note body exceeds **8 000 characters**, `joplin_client.py` truncates it and appends:

```
[TRUNCATED: 12345 chars total]
```

This limit applies to all `get_note.py` calls and the `search_kb.py` helper.
URL content fetched by `save_kb_url.py` is separately truncated at **50 000 characters** before storage.

---

## Exit Codes

| Code | Meaning                 |
|------|-------------------------|
| 0    | Success                 |
| 1    | Any error (see JSON)    |
