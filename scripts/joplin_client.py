"""
joplin_client.py — Shared HTTP client for the Joplin REST API.

All scripts import from this module. Token is read from the environment only
and must never appear in output, logs, or error messages.
"""

import json
import os
import re
import sys

import requests

# Joplin Web Clipper runs on localhost by default
JOPLIN_BASE_URL = "http://localhost:41184"

# Maximum characters to return in note body before truncating
MAX_BODY_CHARS = 8000

# Regex for validating IDs (alphanumeric + dash/underscore only)
_VALID_ID_RE = re.compile(r'^[a-zA-Z0-9_-]+$')


def load_token() -> str:
    """Read JOPLIN_TOKEN from the environment.

    Exits with an error JSON if the variable is not set.
    The token value is never echoed in output.
    """
    token = os.environ.get("JOPLIN_TOKEN", "")
    if not token:
        die("JOPLIN_TOKEN environment variable is not set.")
    return token


def validate_id(value: str, name: str = "id") -> str:
    """Validate that a Joplin resource ID contains only safe characters.

    Raises SystemExit with a JSON error if the value is invalid.
    Error messages never echo the raw value verbatim.
    """
    if not _VALID_ID_RE.match(value):
        die(f"Invalid {name}: must contain only alphanumeric characters, dashes, or underscores.")
    return value


def _auth_params(extra: dict | None = None) -> dict:
    """Build query params dict that includes the auth token."""
    params = {"token": load_token()}
    if extra:
        params.update(extra)
    return params


def _handle_response(resp: requests.Response) -> dict:
    """Parse a Joplin API response and apply standard error handling.

    Returns the parsed JSON dict on success.
    Exits with a JSON error on HTTP error codes.
    """
    if resp.status_code == 401:
        die("Invalid JOPLIN_TOKEN.", code=401)
    if resp.status_code == 404:
        die("Resource not found.", code=404)
    if not resp.ok:
        die(f"Joplin API error (HTTP {resp.status_code}).", code=resp.status_code)

    # Return empty dict for 204 No Content
    if resp.status_code == 204 or not resp.content:
        return {}

    try:
        return resp.json()
    except ValueError:
        die("Joplin returned non-JSON response.")


def _truncate_body(data: dict) -> dict:
    """Truncate the 'body' field of a note dict if it exceeds MAX_BODY_CHARS."""
    if "body" in data and isinstance(data["body"], str):
        original_len = len(data["body"])
        if original_len > MAX_BODY_CHARS:
            data["body"] = data["body"][:MAX_BODY_CHARS] + f"\n[TRUNCATED: {original_len} chars total]"
    return data


def _wrap_note_content(data: dict) -> dict:
    """Wrap the 'body' field in security delimiters so agents can distinguish
    user-controlled data from system instructions."""
    if "body" in data and isinstance(data["body"], str):
        data["body"] = (
            "--- NOTE CONTENT START ---\n"
            + data["body"]
            + "\n--- NOTE CONTENT END ---"
        )
    return data


def joplin_get(path: str, params: dict | None = None) -> dict:
    """Perform a GET request against the Joplin API.

    Args:
        path: API path, e.g. '/notes/abc123'
        params: Additional query parameters (token is added automatically)

    Returns:
        Parsed JSON response dict.
    """
    url = JOPLIN_BASE_URL + path
    try:
        resp = requests.get(url, params=_auth_params(params), timeout=10)
    except requests.exceptions.ConnectionError:
        die("Joplin not reachable. Ensure Joplin is running with Web Clipper enabled.")
    return _handle_response(resp)


def joplin_post(path: str, data: dict | None = None, files=None) -> dict:
    """Perform a POST request against the Joplin API.

    Args:
        path: API path, e.g. '/notes'
        data: Dict sent as JSON body (or as multipart form data fields when files is set)
        files: Optional multipart files dict for resource uploads

    Returns:
        Parsed JSON response dict.
    """
    url = JOPLIN_BASE_URL + path
    params = _auth_params()
    try:
        if files is not None:
            # Multipart upload — data goes as form fields, not JSON
            resp = requests.post(url, params=params, data=data or {}, files=files, timeout=30)
        else:
            resp = requests.post(url, params=params, json=data or {}, timeout=10)
    except requests.exceptions.ConnectionError:
        die("Joplin not reachable. Ensure Joplin is running with Web Clipper enabled.")
    return _handle_response(resp)


def joplin_put(path: str, data: dict) -> dict:
    """Perform a PUT request against the Joplin API.

    Args:
        path: API path, e.g. '/notes/abc123'
        data: Dict sent as JSON body

    Returns:
        Parsed JSON response dict.
    """
    url = JOPLIN_BASE_URL + path
    try:
        resp = requests.put(url, params=_auth_params(), json=data, timeout=10)
    except requests.exceptions.ConnectionError:
        die("Joplin not reachable. Ensure Joplin is running with Web Clipper enabled.")
    return _handle_response(resp)


def joplin_delete(path: str) -> dict:
    """Perform a DELETE request against the Joplin API.

    Args:
        path: API path, e.g. '/notes/abc123'

    Returns:
        Empty dict on success (Joplin returns 204).
    """
    url = JOPLIN_BASE_URL + path
    try:
        resp = requests.delete(url, params=_auth_params(), timeout=10)
    except requests.exceptions.ConnectionError:
        die("Joplin not reachable. Ensure Joplin is running with Web Clipper enabled.")
    return _handle_response(resp)


def ok(data: dict | list) -> None:
    """Print a success JSON response and exit 0."""
    print(json.dumps({"status": "ok", "data": data}))
    sys.exit(0)


def die(message: str, code: int | None = None) -> None:
    """Print an error JSON response and exit 1.

    Never echoes raw user input in the message.
    """
    payload: dict = {"status": "error", "error": message}
    if code is not None:
        payload["code"] = code
    print(json.dumps(payload))
    sys.exit(1)


def get_note_with_wrap(note_id: str) -> dict:
    """Fetch a note by ID, truncate body, and wrap content in security delimiters.

    Convenience helper used by several scripts.
    """
    note_id = validate_id(note_id, "note_id")
    data = joplin_get(
        f"/notes/{note_id}",
        params={"fields": "id,title,body,parent_id,created_time,updated_time"},
    )
    data = _truncate_body(data)
    data = _wrap_note_content(data)
    return data
