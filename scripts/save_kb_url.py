"""
save_kb_url.py — Fetch a public URL and save it as a KB note.

Usage:
    python save_kb_url.py --url "https://example.com/article" \
        --notebook-id <folder_id> [--summary "optional summary"] \
        [--tags "tag1,tag2"]

Security:
- Only http:// and https:// schemes accepted.
- Requests to private/loopback IP ranges are blocked (SSRF prevention).
- Redirect chains validated at each hop; max 5 redirects (PATCH 1).
- DNS pinning: hostname resolved once; pinned IP used for request (PATCH 2).
- IPv4-mapped IPv6 addresses blocked (PATCH 6).
- Content truncated at 50 000 characters.
"""

import argparse
import ipaddress
import re
import socket
import sys
import os
from datetime import date
from urllib.parse import urlparse

import ssl
import urllib3
import certifi as _certifi

sys.path.insert(0, os.path.dirname(__file__))
import joplin_client as jc

try:
    import html2text as _html2text
    _HAS_HTML2TEXT = True
except ImportError:
    _HAS_HTML2TEXT = False

# Maximum characters of page content to store
MAX_CONTENT_CHARS = 50_000

# Private/loopback CIDR ranges to block (SSRF prevention)
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),  # link-local
    ipaddress.ip_network("::1/128"),           # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),          # IPv6 ULA
    ipaddress.ip_network("::ffff:0:0/96"),     # PATCH 6: IPv4-mapped IPv6
]

# CA bundle for TLS verification.
# Runtime deps: urllib3 and certifi (requests itself is NOT imported or called;
# certifi ships with requests if that's how the environment was provisioned, but
# only the certifi and urllib3 packages are used directly here).
_CA_CERTS = _certifi.where()


def _ip_is_blocked(addr: ipaddress._BaseAddress) -> bool:
    """Return True if the address matches any blocked network.
    PATCH 6: also unwraps IPv4-mapped IPv6 and re-checks the mapped IPv4 address.
    """
    for net in _BLOCKED_NETWORKS:
        if addr in net:
            return True
    # PATCH 6: unwrap IPv4-mapped IPv6 (e.g. ::ffff:192.168.1.1) and re-check
    if isinstance(addr, ipaddress.IPv6Address):
        mapped = addr.ipv4_mapped
        if mapped is not None:
            for net in _BLOCKED_NETWORKS:
                if mapped in net:
                    return True
    return False


def _resolve_host(hostname: str) -> list[str]:
    """Resolve *hostname* to a list of IP address strings via a single getaddrinfo call.
    PATCH 2: one resolution point shared by both validation and request construction.
    Returns an empty list if resolution fails (caller must treat as blocked).
    """
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        return []
    return [info[4][0] for info in infos]


def _is_private_host(hostname: str) -> bool:
    """Return True if *hostname* resolves to a private/loopback address.
    PATCH 2: uses _resolve_host() and checks ALL returned IPs.
    PATCH 6: delegates to _ip_is_blocked() which handles IPv4-mapped IPv6.
    """
    ips = _resolve_host(hostname)
    if not ips:
        return True  # Cannot resolve — block rather than allow
    for addr_str in ips:
        try:
            addr = ipaddress.ip_address(addr_str)
        except ValueError:
            continue
        if _ip_is_blocked(addr):
            return True
    return False


def _html_to_text_fallback(html: str) -> str:
    """Strip HTML tags using regex as a fallback when html2text is unavailable."""
    # Remove script and style blocks first
    html = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', html, flags=re.DOTALL | re.IGNORECASE)
    # Strip remaining tags
    text = re.sub(r'<[^>]+>', ' ', html)
    # Collapse whitespace
    return re.sub(r'\s+', ' ', text).strip()


def _extract_title(html: str) -> str:
    """Extract the page title from an HTML document."""
    match = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
    if match:
        return re.sub(r'\s+', ' ', match.group(1)).strip()
    return ""



def _fetch_and_convert(url: str) -> tuple[str, str]:
    """Fetch the URL and return (title, markdown_content).

    PATCH 1: allow_redirects=False; each redirect Location is SSRF-validated
             before following. Chain aborts after 5 hops.
    PATCH 2 (revised): DNS pinning via urllib3 HTTPSConnectionPool.
             TCP connects to the pre-resolved IP; TLS SNI and cert validation
             use the original hostname — fixing the SSLError from the prior
             approach that substituted the IP into the URL itself.
             Redirect TOCTOU fixed: each hop's resolved IPs are carried forward
             from the validation step to the next iteration, eliminating the
             second DNS call that opened a TOCTOU window.
    """
    MAX_REDIRECTS = 5
    current_url = url

    # Resolve the initial hostname once before the loop.
    # All subsequent iterations either use the carried-forward pinned_ip (same
    # hop) or resolve fresh only at redirect-validation time (new hop), with
    # the result immediately carried into the next iteration.
    parsed = urlparse(current_url)
    hostname = parsed.hostname or ""
    if not hostname:
        raise ValueError("URL has no hostname")

    ips = _resolve_host(hostname)
    if not ips:
        raise ValueError(f"Cannot resolve hostname: {hostname!r}")
    for addr_str in ips:
        try:
            addr = ipaddress.ip_address(addr_str)
        except ValueError:
            continue
        if _ip_is_blocked(addr):
            raise ValueError(
                f"SSRF blocked: {hostname!r} resolves to a private/loopback address ({addr_str})"
            )
    pinned_ip = ips[0]

    for redirect_count in range(MAX_REDIRECTS + 1):
        parsed = urlparse(current_url)
        hostname = parsed.hostname or ""
        port = parsed.port or (443 if parsed.scheme == "https" else 80)

        # Build request path (fragments are client-side only, not sent to server)
        path = parsed.path or "/"
        if parsed.params:
            path = f"{path};{parsed.params}"
        if parsed.query:
            path = f"{path}?{parsed.query}"

        req_headers = {
            "User-Agent": "OpenClaw-KB/1.0",
            "Host": hostname,
        }

        # PATCH 2 (revised): urllib3 pool — TCP goes to pinned_ip, TLS SNI and
        # cert validation use the original hostname.  The URL is never rewritten,
        # so ssl.match_hostname() validates against the real domain name.
        if parsed.scheme == "https":
            # Build an explicit SSLContext: stable API across urllib3 1.x and 2.x.
            # Passing ca_certs/cert_reqs as pool kwargs is deprecated in urllib3 2.x
            # and may be silently ignored, which would disable cert validation.
            ssl_ctx = ssl.create_default_context(cafile=_CA_CERTS)
            # ssl_ctx defaults: check_hostname=True, verify_mode=CERT_REQUIRED
            pool = urllib3.HTTPSConnectionPool(
                host=pinned_ip,
                port=port,
                server_hostname=hostname,   # SNI + cert CN/SAN validation
                ssl_context=ssl_ctx,
                timeout=urllib3.Timeout(connect=10, read=10),
            )
        else:
            pool = urllib3.HTTPConnectionPool(
                host=pinned_ip,
                port=port,
                timeout=urllib3.Timeout(connect=10, read=10),
            )

        resp = pool.request(
            "GET", path,
            headers=req_headers,
            redirect=False,         # PATCH 1: manual redirect handling
            preload_content=True,
        )

        # PATCH 1: handle 3xx redirects manually with SSRF validation on each hop
        if resp.status in (301, 302, 303, 307, 308):
            if redirect_count >= MAX_REDIRECTS:
                raise ValueError(f"Too many redirects (max {MAX_REDIRECTS})")

            location = resp.headers.get("Location", "").strip()
            if not location:
                raise ValueError("Redirect response is missing a Location header")

            # Resolve relative redirects against the current origin
            if location.startswith("/"):
                orig = urlparse(current_url)
                location = f"{orig.scheme}://{orig.netloc}{location}"

            loc_parsed = urlparse(location)
            if loc_parsed.scheme not in ("http", "https"):
                raise ValueError(
                    f"Redirect to non-HTTP/S scheme blocked: {loc_parsed.scheme!r}"
                )

            # Block HTTPS → HTTP downgrade
            # `parsed` is urlparse(current_url) set at the top of this iteration.
            if parsed.scheme == "https" and loc_parsed.scheme == "http":
                raise ValueError("Redirect blocked: HTTPS→HTTP downgrade not permitted")

            loc_hostname = loc_parsed.hostname or ""
            if not loc_hostname:
                raise ValueError("Redirect Location header has no hostname")

            # Resolve once for SSRF validation; carry the result forward so the
            # next iteration uses the same IPs without a second DNS call.
            # This closes the redirect TOCTOU window (medium-severity issue).
            loc_ips = _resolve_host(loc_hostname)
            if not loc_ips:
                raise ValueError(f"Cannot resolve redirect hostname: {loc_hostname!r}")
            for addr_str in loc_ips:
                try:
                    addr = ipaddress.ip_address(addr_str)
                except ValueError:
                    continue
                if _ip_is_blocked(addr):
                    raise ValueError(
                        f"SSRF blocked: redirect target {loc_hostname!r} resolves to a "
                        f"private address ({addr_str})"
                    )

            # Carry validated IPs into the next hop — no re-resolution needed
            pinned_ip = loc_ips[0]
            current_url = location
            continue  # Follow validated redirect

        # Non-redirect: raise on HTTP error, then exit loop
        if resp.status >= 400:
            raise ValueError(f"HTTP error {resp.status}")
        break

    content_type = resp.headers.get("Content-Type", "")
    raw = resp.data.decode("utf-8", errors="replace")

    title = _extract_title(raw) if "html" in content_type else ""

    if "html" in content_type:
        if _HAS_HTML2TEXT:
            h = _html2text.HTML2Text()
            h.ignore_links = False
            h.ignore_images = True
            h.body_width = 0  # no wrapping
            markdown = h.handle(raw)
        else:
            markdown = _html_to_text_fallback(raw)
    else:
        markdown = raw

    # Truncate to limit
    if len(markdown) > MAX_CONTENT_CHARS:
        markdown = markdown[:MAX_CONTENT_CHARS] + f"\n\n[TRUNCATED: content exceeds {MAX_CONTENT_CHARS} chars]"

    return title, markdown


def main():
    parser = argparse.ArgumentParser(description="Save a webpage as a KB note")
    parser.add_argument("--url", required=True, help="URL to fetch (http/https only)")
    parser.add_argument("--summary", default="", help="Optional summary (auto-generated if omitted)")
    parser.add_argument("--notebook-id", required=True, help="Target notebook ID")
    parser.add_argument("--tags", default="", help="Comma-separated tag names (optional)")
    args = parser.parse_args()

    # --- Scheme validation ---
    parsed = urlparse(args.url)
    if parsed.scheme not in ("http", "https"):
        jc.die("Only http:// and https:// URLs are allowed.")

    hostname = parsed.hostname or ""
    if not hostname:
        jc.die("URL hostname is missing or invalid.")

    # --- SSRF prevention ---
    if _is_private_host(hostname):
        jc.die("Requests to private or loopback addresses are not allowed.")

    notebook_id = jc.validate_id(args.notebook_id, "notebook_id")

    # --- Fetch and convert ---
    try:
        page_title, content = _fetch_and_convert(args.url)
    except Exception as exc:
        jc.die(f"Failed to fetch URL: {type(exc).__name__}")

    title = page_title or args.url
    summary = args.summary or f"Webpage captured from {parsed.netloc}"

    today = date.today().strftime("%Y-%m-%d")
    # PATCH 5: sanitize URL to prevent newline injection in frontmatter
    safe_url = args.url.replace('\n', ' ').replace('\r', ' ')
    kb_body = (
        f"---\n"
        f"kb_source: {safe_url}\n"
        f"kb_type: webpage\n"
        f"kb_captured: {today}\n"
        f"---\n\n"
        f"## Summary\n{summary}\n\n"
        f"## Content\n{content}"
    )

    note = jc.joplin_post("/notes", data={
        "title": title,
        "body": kb_body,
        "parent_id": notebook_id,
    })
    note_id = note.get("id")

    # Apply tags using the shared helper from save_kb_text
    if args.tags:
        from save_kb_text import apply_tags
        apply_tags(note_id, args.tags)

    jc.ok({"id": note_id, "title": title, "kb_type": "webpage", "url": args.url})


if __name__ == "__main__":
    main()
