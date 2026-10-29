#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["markdown>=3.6", "edn-format>=0.7.5"]
# ///
"""Publish documents as NOISE-styled pages on pls.n0.beer.

  pls.py publish <file> [--ttl 24h] [--title T] [--page-name P] [--raw] [--wrap]
  pls.py render  <file> [same options] [-o out.html]
  pls.py list
  pls.py delete  <url-or-id>

Environment:
  NOISE_PLS_BASE   server base URL (default https://pls.n0.beer)
  NOISE_PLS_TOKEN  NOISE-SIG-1 bootstrap signing key (pls.publish.0);
                   falls back to the macOS Keychain item
                   "noise-pls-publish" (account "default"), then the NOISE
                   repo's root secrets.edn under :pls-site :publish-token
  NOISE_PLS_SECRETS_FILE  optional path to that existing secrets.edn file
"""

from __future__ import annotations

import argparse
import base64
import html
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from collections.abc import Mapping

import markdown
from edn_format import Keyword, loads as load_edn
from noise_sig import self_check, sign_headers

DEFAULT_BASE = "https://pls.n0.beer"
BASE_ENV = "NOISE_PLS_BASE"
TOKEN_ENV = "NOISE_PLS_TOKEN"
SECRETS_FILE_ENV = "NOISE_PLS_SECRETS_FILE"
KEYCHAIN_SERVICE = "noise-pls-publish"
KEYCHAIN_ACCOUNT = "default"
USER_AGENT = "noise-bot"

TTL_MIN, TTL_MAX, TTL_DEFAULT = 60, 604_800, "24h"
MAX_BYTES = 16 * 1024 * 1024

TEMPLATE = Path(__file__).resolve().parent.parent / "template.html"
MARKDOWN_SUFFIXES = {".md", ".markdown", ".txt"}
HTML_SUFFIXES = {".html", ".htm"}
MARKDOWN_EXTENSIONS = ["tables", "fenced_code", "sane_lists", "toc", "attr_list"]

DEFAULT_PAGE_NAME = "Shared page"


class PlsError(Exception):
    """A failure to report on stderr, exiting non-zero."""


def die(message: str) -> None:
    raise PlsError(message)


# ---------------------------------------------------------------- time ----

_UNITS = {"s": 1, "m": 60, "h": 3600, "d": 86_400, "w": 604_800}


def parse_ttl(value: str) -> int:
    """Seconds from `90m`, `24h`, `3d`, `1d12h` or a bare number of seconds."""
    text = value.strip().lower()
    if text.isdigit():
        seconds = int(text)
    elif re.fullmatch(r"(?:\d+[smhdw])+", text):
        seconds = sum(int(n) * _UNITS[u] for n, u in re.findall(r"(\d+)([smhdw])", text))
    else:
        raise argparse.ArgumentTypeError(
            f"invalid duration {value!r}; use forms like 90m, 24h, 3d, 7d"
        )
    if not TTL_MIN <= seconds <= TTL_MAX:
        raise argparse.ArgumentTypeError("must be between 60s and 7d")
    return seconds


def date_stamp(moment: datetime) -> str:
    """`5 Oct 2026`."""
    return f"{moment.day} {moment:%b} {moment.year}"


def long_local(moment: datetime) -> str:
    """Terminal form: `Mon 6 Oct 2026, 1:05 PM EDT`."""
    local = moment.astimezone()
    return (
        f"{local:%a} {local.day} {local:%b} {local.year}, "
        f"{local.hour % 12 or 12}:{local:%M} {local:%p} {local:%Z}"
    ).strip()


def page_local(moment: datetime) -> str:
    """Page-footer form, on the house 24-hour clock: `Mon 6 Oct 2026, 13:05 EDT`."""
    local = moment.astimezone()
    return f"{local:%a} {local.day} {local:%b} {local.year}, {local:%H:%M} {local:%Z}".strip()


def short_local(moment: datetime) -> str:
    """List form: `Mon 6 Oct, 1:05 PM`."""
    local = moment.astimezone()
    return f"{local:%a} {local.day} {local:%b}, {local.hour % 12 or 12}:{local:%M} {local:%p}"


def parse_iso(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def human_bytes(count: int) -> str:
    if count < 1024:
        return f"{count} B"
    if count < 1024 * 1024:
        return f"{count / 1024:.1f} KiB"
    return f"{count / (1024 * 1024):.2f} MiB"


# ---------------------------------------------------------------- build ----

_TEMPLATE_FIELD = re.compile(r"\{\{(title|page_name|stamp|body|footer)\}\}")
_TABLE = re.compile(r'(<div\s+class="scroll"\s*>\s*)?(<table\b.*?</table>)', re.S | re.I)
_RIGHT_CELL = re.compile(r'<(t[dh])\s+style="text-align:\s*right;?"\s*>', re.I)
_H1 = re.compile(r"<h1[\s>]", re.I)
_STYLESHEET_LINK = re.compile(r'<link rel="stylesheet" href="[^"]*/_/pls\.css">')
_FONT_URL = re.compile(r"""url\((['"]?)(/_/fonts/[A-Za-z0-9._-]+\.woff2)\1\)""")


def esc(text: str) -> str:
    return html.escape(text, quote=True)


def plain_text(fragment: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", "", fragment)).split())


def first_h1_text(body: str) -> str | None:
    match = re.search(r"<h1\b[^>]*>(.*?)</h1\s*>", body, re.S | re.I)
    text = plain_text(match.group(1)) if match else ""
    return text or None


def head_title(document: str) -> str | None:
    match = re.search(r"<title\b[^>]*>(.*?)</title\s*>", document, re.S | re.I)
    text = plain_text(match.group(1)) if match else ""
    return text or None


def wrap_tables(body: str) -> str:
    """Put every table in div.scroll (leave ones already wrapped alone)."""

    def wrap(match: re.Match[str]) -> str:
        if match.group(1):
            return match.group(0)
        return f'<div class="scroll">{match.group(2)}</div>'

    return _TABLE.sub(wrap, body)


def finish_body(body: str, title: str) -> str:
    """Wrap tables, give right-aligned cells the .num class, ensure one h1."""
    body = _RIGHT_CELL.sub(r'<\1 class="num">', body)
    body = wrap_tables(body)
    if not _H1.search(body):
        body = f"<h1>{esc(title)}</h1>\n{body}"
    return body


def render_markdown(text: str) -> str:
    return markdown.Markdown(extensions=MARKDOWN_EXTENSIONS).convert(text)


def extract_body(document: str) -> tuple[str, str | None]:
    """Body content of a full HTML document, minus its own <style> and <script>."""
    match = re.search(r"<body\b[^>]*>(.*)</body\s*>", document, re.S | re.I)
    if match:
        inner = match.group(1)
    else:
        inner = re.sub(
            r"<!doctype[^>]*>|</?html\b[^>]*>|<head\b.*?</head\s*>",
            "",
            document,
            flags=re.S | re.I,
        )
    if re.search(r"<(style|script)\b", inner, re.I):
        print(
            "pls: note: dropped <style>/<script> from the document; the NOISE shell supplies the design.",
            file=sys.stderr,
        )
        inner = re.sub(r"<(style|script)\b.*?</\1\s*>", "", inner, flags=re.S | re.I)
    return inner.strip(), head_title(document)


def read_text(path: Path, data: bytes) -> str:
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        die(f"{path} is not valid UTF-8 text.")
        raise  # unreachable


def fetch_asset(base: str, path: str) -> bytes:
    request = urllib.request.Request(base + path, headers={"User-Agent": USER_AGENT})
    try:
        with _OPENER.open(request, timeout=30) as response:
            if response.status == 200:
                return response.read()
            die(f"Could not fetch {base}{path} [HTTP {response.status}].")
    except urllib.error.HTTPError as err:
        die(f"Could not fetch {base}{path} [HTTP {err.code}].")
    except (urllib.error.URLError, TimeoutError, OSError) as err:
        die(f"Could not fetch {base}{path} ({getattr(err, 'reason', err)}).")
    raise AssertionError  # unreachable


def inline_stylesheet(base: str) -> str:
    """The server's current pls.css as a <style> block, its faces as data: URIs.

    The page becomes one self-contained file: a snapshot of the design at publish
    time that renders offline and never depends on /_/ again."""
    css = fetch_asset(base, "/_/pls.css").decode("utf-8")
    fonts: dict[str, str] = {}

    def embed(match: re.Match[str]) -> str:
        path = match.group(2)
        if path not in fonts:
            fonts[path] = base64.b64encode(fetch_asset(base, path)).decode("ascii")
        return f"url(data:font/woff2;base64,{fonts[path]})"

    css = _FONT_URL.sub(embed, css)
    return "<style>\n" + css.replace("</", "<\\/") + "\n</style>"


def shell(body: str, *, title: str, page_name: str, footer: str, base: str, inline: bool) -> bytes:
    template = TEMPLATE.read_text(encoding="utf-8")
    if base != DEFAULT_BASE:
        template = template.replace(f"{DEFAULT_BASE}/_/pls.css", esc(f"{base}/_/pls.css"))
    values = {
        "title": esc(title),
        "page_name": esc(page_name),
        "stamp": esc(date_stamp(datetime.now().astimezone())),
        "body": body,
        "footer": esc(footer),
    }
    # One pass, so a document that mentions {{title}} is never substituted.
    page = _TEMPLATE_FIELD.sub(lambda m: values[m.group(1)], template)
    if inline:
        # count=1: the shell's own <head> link comes before any body content.
        style = inline_stylesheet(base)
        page = _STYLESHEET_LINK.sub(lambda m: style, page, count=1)
    return page.encode("utf-8")


def prepare(
    path: Path, args: argparse.Namespace, *, base: str, footer: str, inline: bool
) -> tuple[bytes, str]:
    """Final bytes to publish and how they were made: raw, as-is or wrapped."""
    if not path.is_file():
        die(f"No such file: {path}")
    data = path.read_bytes()
    if args.raw:
        return data, "raw"

    suffix = path.suffix.lower()
    if suffix in MARKDOWN_SUFFIXES:
        body = render_markdown(read_text(path, data))
        found = first_h1_text(body)
    elif suffix in HTML_SUFFIXES:
        text = read_text(path, data)
        if re.search(r"<html|<!doctype", text, re.I):
            if not args.wrap:
                if args.title or args.page_name:
                    print(
                        "pls: note: --title/--page-name ignored; the full document is published as-is "
                        "(use --wrap for the NOISE shell).",
                        file=sys.stderr,
                    )
                return data, "as-is"
            body, doc_title = extract_body(text)
            found = first_h1_text(body) or doc_title
        else:
            body = text
            found = first_h1_text(body)
    else:
        die(
            f"Unsupported file type {suffix or '(none)'!r}. Write Markdown or an HTML body first "
            "(see SKILL.md), or pass --raw to publish the bytes untouched."
        )

    title = args.title or found or path.stem
    page = shell(
        finish_body(body, title),
        title=title,
        page_name=args.page_name or DEFAULT_PAGE_NAME,
        footer=footer,
        base=base,
        inline=inline,
    )
    return page, "wrapped, stylesheet embedded" if inline else "wrapped"


# ---------------------------------------------------------------- HTTP ----


def get_base() -> str:
    return (os.environ.get(BASE_ENV) or DEFAULT_BASE).strip().rstrip("/")


def get_token() -> str:
    token = os.environ.get(TOKEN_ENV, "").strip()
    if token:
        return token
    if sys.platform == "darwin" and shutil.which("security"):
        try:
            result = subprocess.run(
                [
                    "security",
                    "find-generic-password",
                    "-a", KEYCHAIN_ACCOUNT,
                    "-s", KEYCHAIN_SERVICE,
                    "-w",
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
        except (OSError, subprocess.TimeoutExpired):
            result = None
        if result and result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    configured_path = os.environ.get(SECRETS_FILE_ENV, "").strip()
    paths = (
        [Path(configured_path).expanduser()]
        if configured_path
        else [Path.home() / root / "noise" / "secrets.edn" for root in ("Github", "github", "GitHub")]
    )
    for path in paths:
        if not path.is_file() and not configured_path:
            continue
        try:
            config = load_edn(path.read_text(encoding="utf-8"))
            site = config.get(Keyword("pls-site")) if isinstance(config, Mapping) else None
            token = site.get(Keyword("publish-token")) if isinstance(site, Mapping) else None
        except Exception:
            # Parser errors can contain credential values; never display them.
            die(f"Could not read publish token from {path}. Check the existing secrets.edn file.")
        if isinstance(token, str) and token.strip():
            return token.strip()
        if configured_path:
            die(f"No :pls-site :publish-token string found in {path}.")
    die(
        "No publish token found.\n"
        f"  Set {TOKEN_ENV}, or point {SECRETS_FILE_ENV} at the NOISE repo's root secrets.edn.\n"
        "  The token belongs under :pls-site :publish-token; do not copy it into another file.\n"
        f"  On macOS, the Keychain item {KEYCHAIN_SERVICE} (account {KEYCHAIN_ACCOUNT}) is also supported."
    )
    raise AssertionError  # unreachable


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Never forward a signed request to another target."""

    def redirect_request(self, *args, **kwargs):  # noqa: ANN002, ANN003
        return None


_OPENER = urllib.request.build_opener(_NoRedirect)


def api(
    method: str, path: str, *, base: str, token: str, body: bytes | None = None, timeout: int = 120
) -> dict:
    self_check()
    request = urllib.request.Request(base + path, data=body, method=method)
    content_type = "text/html; charset=utf-8" if body is not None else None
    headers = sign_headers(token, "pls", "pls.publish.0", method, request.selector,
                           body or b"", content_type)
    for name, value in headers.items():
        request.add_header(name, value)
    request.add_header("User-Agent", USER_AGENT)
    request.add_header("Accept", "application/json")
    if content_type is not None:
        request.add_header("Content-Type", content_type)
    try:
        with _OPENER.open(request, timeout=timeout) as response:
            status, raw = response.status, response.read()
    except urllib.error.HTTPError as err:
        status, raw = err.code, err.read()
    except urllib.error.URLError as err:
        die(
            f"Could not reach {base} ({err.reason}). The pls service may not be deployed yet, "
            f"or this machine is offline. Set {BASE_ENV} to use a different server."
        )
    except (TimeoutError, OSError) as err:
        die(f"Request to {base} failed ({err}). The pls service may be down or unreachable.")

    try:
        data = json.loads(raw)
    except ValueError:
        data = None
    if status < 400 and isinstance(data, dict) and data.get("ok"):
        return data
    if isinstance(data, dict) and data.get("error"):
        code = f" ({data['errorCode']})" if data.get("errorCode") else ""
        die(f"{data['error']}{code} [HTTP {status}]")
    snippet = raw[:200].decode("utf-8", "replace").strip()
    die(f"Unexpected response from {base} [HTTP {status}]" + (f": {snippet}" if snippet else ""))
    raise AssertionError  # unreachable


# ------------------------------------------------------------- commands ----


def cmd_publish(args: argparse.Namespace) -> None:
    base = get_base()
    expires = datetime.now().astimezone() + timedelta(seconds=args.ttl)
    footer = f"Shared from {urllib.parse.urlsplit(base).netloc}. Expires {page_local(expires)}."
    data, kind = prepare(Path(args.path).expanduser(), args, base=base, footer=footer,
                         inline=args.inline)
    if len(data) > MAX_BYTES:
        die(f"Page is {human_bytes(len(data))}; the limit is 16 MiB.")
    token = get_token()
    result = api("POST", f"/v1/pages?ttl={args.ttl}", base=base, token=token, body=data)
    expires_at = parse_iso(result.get("expiresAt")) or expires
    print(f"URL:     {result.get('url', '(none returned)')}")
    print(f"Expires: {long_local(expires_at)}")
    print(f"Size:    {human_bytes(int(result.get('bytes') or len(data)))} ({kind})")


def cmd_render(args: argparse.Namespace) -> None:
    footer = "Preview, not published."
    path, base = Path(args.path).expanduser(), get_base()
    try:
        data, kind = prepare(path, args, base=base, footer=footer, inline=args.inline)
    except PlsError as err:
        if not args.inline or "Could not fetch" not in str(err):
            raise
        print(f"pls: note: {err} Rendering with a linked stylesheet instead.", file=sys.stderr)
        data, kind = prepare(path, args, base=base, footer=footer, inline=False)
    if not args.output or args.output == "-":
        sys.stdout.write(data.decode("utf-8", "replace"))
        return
    out = Path(args.output).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)
    print(f"Wrote {out} ({human_bytes(len(data))}, {kind})")


def cmd_list(args: argparse.Namespace) -> None:
    base = get_base()
    result = api("GET", "/v1/pages", base=base, token=get_token())
    pages = result.get("pages") or []
    if not pages:
        print("No published pages.")
        return
    rows = []
    for page in pages:
        created, expires = parse_iso(page.get("createdAt")), parse_iso(page.get("expiresAt"))
        title = str(page.get("title") or "")
        rows.append(
            (
                str(page.get("ref", "")),
                title if len(title) <= 40 else title[:37] + "...",
                short_local(created) if created else "",
                short_local(expires) if expires else "",
                human_bytes(int(page.get("bytes") or 0)),
            )
        )
    header = ("Ref", "Title", "Created", "Expires", "Size")
    widths = [max(len(r[i]) for r in [header, *rows]) for i in range(5)]
    for row in [header, *rows]:
        print("  ".join(cell.ljust(widths[i]) for i, cell in enumerate(row)).rstrip())


def page_id(target: str) -> str:
    """The id from a page URL, or the id itself."""
    target = target.strip()
    if "/" in target:
        target = urllib.parse.urlsplit(target).path.rstrip("/").rsplit("/", 1)[-1]
    if not re.fullmatch(r"[A-Za-z0-9_-]+", target):
        die("Give a page URL like https://pls.n0.beer/<id>, or the id itself.")
    return target


def cmd_delete(args: argparse.Namespace) -> None:
    ident = page_id(args.target)
    api(
        "DELETE",
        f"/v1/pages/{urllib.parse.quote(ident, safe='')}",
        base=get_base(),
        token=get_token(),
    )
    print(f"Deleted {ident}.")


# ------------------------------------------------------------------ CLI ----


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pls.py",
        description="Publish documents as NOISE-styled pages on pls.n0.beer.",
        epilog=f"Environment: {BASE_ENV} (default {DEFAULT_BASE}), {TOKEN_ENV}, "
        f"{SECRETS_FILE_ENV} (existing NOISE secrets.edn; macOS Keychain is also supported).",
    )
    sub = parser.add_subparsers(dest="command", required=True, metavar="command")

    def build_options(p: argparse.ArgumentParser) -> None:
        p.add_argument("path", help=".md/.markdown/.txt (Markdown), .html/.htm (fragment or full document)")
        p.add_argument("--ttl", type=parse_ttl, default=parse_ttl(TTL_DEFAULT),
                       help="how long the page lives: 90m, 24h, 3d, 7d (60s to 7d, default 24h)")
        p.add_argument("--title", help="page title (default: first h1, else the file name)")
        p.add_argument("--page-name", help=f"masthead label (default: {DEFAULT_PAGE_NAME!r})")
        mode = p.add_mutually_exclusive_group()
        mode.add_argument("--raw", action="store_true", help="send the file bytes untouched")
        mode.add_argument("--wrap", action="store_true",
                          help="put a full HTML document's body in the NOISE shell (default: publish it as-is)")
        p.add_argument("--inline", action="store_true",
                       help="embed the stylesheet and fonts so the page is one self-contained file "
                            "(about 216 KiB; default links the cached /_/pls.css)")

    publish = sub.add_parser("publish", help="publish a file and print its URL")
    build_options(publish)
    publish.set_defaults(func=cmd_publish)

    render = sub.add_parser("render", help="build the final HTML locally without publishing")
    build_options(render)
    render.add_argument("-o", "--output", help="write here (default: stdout)")
    render.set_defaults(func=cmd_render)

    listing = sub.add_parser("list", help="list your published pages")
    listing.set_defaults(func=cmd_list)

    delete = sub.add_parser("delete", help="delete a page by URL or id")
    delete.add_argument("target", help="page URL or id")
    delete.set_defaults(func=cmd_delete)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        args.func(args)
    except PlsError as err:
        print(f"pls: error: {err}", file=sys.stderr)
        return 1
    except BrokenPipeError:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
