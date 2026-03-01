# Joplin OpenClaw Skill — Manual Integration Test Checklist

> Run these tests in order against a live Joplin instance. Each section depends on the one before it.

---

## 1. Prerequisites

- [ ] Joplin desktop app is running with the Web Clipper / local REST API enabled (default port 41184)
- [ ] `JOPLIN_TOKEN` environment variable is set to your Joplin API token
- [ ] Python dependencies installed: `pip install requests urllib3 certifi html2text`
- [ ] Skill scripts are present in the Joplin skill directory

---

## 2. Setup Verification

- [ ] Ping the Joplin API: `curl http://localhost:41184/ping?token=$JOPLIN_TOKEN` → returns `JoplinClipperServer`
- [ ] Run `list_notebooks` and confirm at least one notebook is returned
- [ ] Record a test notebook ID as `$TEST_NB_ID` for use in subsequent steps

---

## 3. Core Note CRUD

### Create
- [ ] Create a note in `$TEST_NB_ID`:
  ```
  python create_note.py --notebook $TEST_NB_ID --title "Integration Test Note" --body "Hello, Joplin!"
  ```
- [ ] Verify the command exits 0 and prints a note ID
- [ ] Record the returned ID as `$NOTE_ID`

### Get
- [ ] Retrieve the note: `python get_note.py --id $NOTE_ID`
- [ ] Verify title is `Integration Test Note` and body contains `Hello, Joplin!`
- [ ] Verify output contains `--- NOTE CONTENT START ---` / `--- NOTE CONTENT END ---` delimiters (see §9)

### Update
- [ ] Update the note body:
  ```
  python update_note.py --id $NOTE_ID --body "Updated body content"
  ```
- [ ] Run `get_note` again and verify body is now `Updated body content`

### Append
- [ ] Append text to the note:
  ```
  python append_note.py --id $NOTE_ID --text "Appended line"
  ```
- [ ] Run `get_note` and verify body ends with `Appended line`

### Delete
- [ ] Delete the note: `python delete_note.py --id $NOTE_ID`
- [ ] Attempt `get_note --id $NOTE_ID` and verify it returns a 404 / not-found error

---

## 4. Notebook Operations

### List Notebooks
- [ ] Run `python list_notebooks.py` and verify all notebooks are listed with IDs and titles
- [ ] Run `python list_notebooks.py --limit 1` and verify exactly one result is returned

### List Notes in Notebook
- [ ] Create at least two notes in `$TEST_NB_ID` for this test
- [ ] Run `python list_notes.py --notebook $TEST_NB_ID` and verify both notes appear
- [ ] Run `python list_notes.py --notebook $TEST_NB_ID --limit 1` and verify exactly one result is returned

---

## 5. Tag Operations

- [ ] Create a note to tag:
  ```
  python create_note.py --notebook $TEST_NB_ID --title "Tag Test Note" --body "Tagging test"
  ```
- [ ] Record the returned ID as `$TAG_NOTE_ID`
- [ ] Add a tag: `python add_tag.py --id $TAG_NOTE_ID --tag "integration-test"`
- [ ] Verify tag: `python get_note.py --id $TAG_NOTE_ID` — confirm `integration-test` appears in tags
- [ ] Remove the tag: `python remove_tag.py --note-id $TAG_NOTE_ID --tag "integration-test"`
- [ ] Verify tag removed: run `get_note` again and confirm `integration-test` is absent from tags

---

## 6. Search

- [ ] Create a note with unique content for search:
  ```
  python create_note.py --notebook $TEST_NB_ID --title "Search Target Note" --body "xyzzy_unique_search_term"
  ```
- [ ] Record the returned ID as `$SEARCH_NOTE_ID`
- [ ] Run `python search_notes.py --query "xyzzy_unique_search_term"` and verify `$SEARCH_NOTE_ID` appears in results
- [ ] Run `python search_notes.py --query "xyzzy_unique_search_term" --limit 1` and verify exactly one result is returned
- [ ] Verify output contains `--- NOTE CONTENT START ---` / `--- NOTE CONTENT END ---` delimiters (see §9)

---

## 7. Knowledge Base Saves

### save_kb_text.py
- [ ] Run:
  ```
  python save_kb_text.py --notebook $TEST_NB_ID --title "KB Text Test" --text "Plain text KB entry"
  ```
- [ ] Verify note is created and retrievable

### save_kb_url.py
- [ ] Run:
  ```
  python save_kb_url.py --notebook $TEST_NB_ID --url "https://example.com" --title "KB URL Test"
  ```
- [ ] Verify note is created with page content extracted from https://example.com
- [ ] Verify no SSRF rejection (example.com is a public host — should succeed)

### save_kb_image.py
- [ ] Place a small image file inside your home directory, e.g. `~/test-image.png`
- [ ] Run:
  ```
  python save_kb_image.py --notebook $TEST_NB_ID --file ~/test-image.png --title "KB Image Test"
  ```
- [ ] Verify note is created with the image embedded or linked

### save_kb_file.py — Small File (inline content)
- [ ] Create a small text file inside your home directory, e.g. `~/test-small.txt` (< 5 MB)
- [ ] Run:
  ```
  python save_kb_file.py --notebook $TEST_NB_ID --file ~/test-small.txt --title "KB Small File Test"
  ```
- [ ] Verify note is created with inline file content

### save_kb_file.py — Large File (path reference)
- [ ] Prepare a file larger than 5 MB inside your home directory, e.g. `~/test-large.bin`
- [ ] Run:
  ```
  python save_kb_file.py --notebook $TEST_NB_ID --file ~/test-large.bin --title "KB Large File Test"
  ```
- [ ] Verify the note is created with a path reference (not inline content) due to the 5 MB limit
- [ ] Verify the note body contains the file path rather than raw file data

---

## 8. Security Checks

### Path Restriction — Outside Home Directory
- [ ] Run `save_kb_file.py` with a path outside the home directory (use a safe placeholder):
  ```
  python save_kb_file.py --notebook $TEST_NB_ID --file /path/outside/home --title "Security Test"
  ```
- [ ] Verify the command is **rejected** with a path restriction error (does not read or save the file)

### Path Traversal
- [ ] Run `save_kb_file.py` with a traversal path:
  ```
  python save_kb_file.py --notebook $TEST_NB_ID --file ~/../../outside/home --title "Traversal Test"
  ```
- [ ] Verify the command is **rejected** with a path traversal / restriction error

### SSRF — Localhost
- [ ] Run `save_kb_url.py` targeting the Joplin API itself:
  ```
  python save_kb_url.py --notebook $TEST_NB_ID --url "http://127.0.0.1:41184/ping" --title "SSRF Test 1"
  ```
- [ ] Verify the command is **rejected** with an SSRF / private address error

### SSRF — Private Network
- [ ] Run `save_kb_url.py` targeting a private LAN address:
  ```
  python save_kb_url.py --notebook $TEST_NB_ID --url "http://192.168.1.1" --title "SSRF Test 2"
  ```
- [ ] Verify the command is **rejected** with an SSRF / private address error

### Limit Validation — Rejected Values
- [ ] Run `list_notes.py --notebook $TEST_NB_ID --limit 0` → verify **rejected** (out of range)
- [ ] Run `list_notes.py --notebook $TEST_NB_ID --limit 101` → verify **rejected** (out of range)

### Limit Validation — Accepted Values
- [ ] Run `list_notes.py --notebook $TEST_NB_ID --limit 1` → verify **accepted** and returns ≤ 1 result
- [ ] Run `list_notes.py --notebook $TEST_NB_ID --limit 100` → verify **accepted** and returns ≤ 100 results

---

## 9. Content Delimiter Verification

- [ ] Run `python get_note.py --id $SEARCH_NOTE_ID` and confirm output contains:
  - `--- NOTE CONTENT START ---` at the start of the body field
  - `--- NOTE CONTENT END ---` at the end of the body field
- [ ] Run `python search_notes.py --query "xyzzy_unique_search_term"` and confirm each result block contains equivalent `NOTE CONTENT START` / `NOTE CONTENT END` wrappers
- [ ] Verify no field content bleeds across delimiter boundaries

---

## 10. Cleanup

- [ ] Delete all notes created during this test run (use `delete_note.py --id <id>` for each):
  - `$NOTE_ID` (if not already deleted in §3)
  - `$TAG_NOTE_ID`
  - `$SEARCH_NOTE_ID`
  - KB Text Test note
  - KB URL Test note
  - KB Image Test note
  - KB Small File Test note
  - KB Large File Test note
  - Notes created for notebook listing (§4)
- [ ] Remove the `integration-test` tag from Joplin if it persists (via Joplin UI or API)
- [ ] Verify no leftover test notes remain in `$TEST_NB_ID`

---

*Created: 2026-03-01. Run after Joplin desktop is installed on the target machine.*
