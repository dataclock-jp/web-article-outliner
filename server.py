from __future__ import annotations

import argparse
import datetime as dt
import html
from html.parser import HTMLParser
import json
import mimetypes
import os
from pathlib import Path
import re
import sqlite3
from typing import Any
from urllib.parse import parse_qs, urlparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "articles.db"
MAX_REQUEST_BYTES = 15 * 1024 * 1024


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def connect_db() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            source_url TEXT NOT NULL DEFAULT '',
            html TEXT NOT NULL,
            text_content TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_articles_updated ON articles(updated_at DESC)")
    conn.commit()
    return conn


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style", "noscript", "template"}:
            self.skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "noscript", "template"} and self.skip_depth:
            self.skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self.skip_depth:
            text = data.strip()
            if text:
                self.parts.append(text)

    def text(self) -> str:
        return re.sub(r"\s+", " ", " ".join(self.parts)).strip()


class HtmlSanitizer(HTMLParser):
    allowed_tags = {
        "a",
        "abbr",
        "article",
        "aside",
        "b",
        "blockquote",
        "br",
        "caption",
        "cite",
        "code",
        "col",
        "colgroup",
        "dd",
        "del",
        "details",
        "dfn",
        "div",
        "dl",
        "dt",
        "em",
        "figcaption",
        "figure",
        "footer",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "header",
        "hr",
        "i",
        "img",
        "ins",
        "kbd",
        "li",
        "main",
        "mark",
        "ol",
        "p",
        "pre",
        "q",
        "s",
        "samp",
        "section",
        "small",
        "span",
        "strong",
        "sub",
        "summary",
        "sup",
        "table",
        "tbody",
        "td",
        "tfoot",
        "th",
        "thead",
        "time",
        "tr",
        "u",
        "ul",
        "var",
    }
    void_tags = {"br", "hr", "img", "col"}
    blocked_tags = {"script", "style", "iframe", "object", "embed", "form", "input", "button", "textarea", "select", "option", "template", "svg", "canvas", "video", "audio"}
    global_attrs = {"class", "title", "lang", "dir", "style"}
    tag_attrs = {
        "a": {"href"},
        "img": {"src", "alt", "width", "height", "loading"},
        "td": {"colspan", "rowspan"},
        "th": {"colspan", "rowspan", "scope"},
        "time": {"datetime"},
        "col": {"span", "width"},
    }
    allowed_css = {
        "background",
        "background-color",
        "border",
        "border-bottom",
        "border-collapse",
        "border-color",
        "border-left",
        "border-radius",
        "border-right",
        "border-spacing",
        "border-style",
        "border-top",
        "border-width",
        "color",
        "display",
        "font-family",
        "font-size",
        "font-style",
        "font-weight",
        "height",
        "letter-spacing",
        "line-height",
        "list-style",
        "margin",
        "margin-bottom",
        "margin-left",
        "margin-right",
        "margin-top",
        "max-width",
        "min-width",
        "opacity",
        "padding",
        "padding-bottom",
        "padding-left",
        "padding-right",
        "padding-top",
        "text-align",
        "text-decoration",
        "vertical-align",
        "white-space",
        "width",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.output: list[str] = []
        self.open_tags: list[str] = []
        self.skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in self.blocked_tags:
            self.skip_depth += 1
            return
        if self.skip_depth or tag not in self.allowed_tags:
            return

        attr_text = self._sanitize_attrs(tag, attrs)
        self.output.append(f"<{tag}{attr_text}>")
        if tag not in self.void_tags:
            self.open_tags.append(tag)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if self.skip_depth or tag not in self.allowed_tags or tag in self.blocked_tags:
            return
        attr_text = self._sanitize_attrs(tag, attrs)
        self.output.append(f"<{tag}{attr_text}>")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in self.blocked_tags:
            if self.skip_depth:
                self.skip_depth -= 1
            return
        if self.skip_depth or tag not in self.allowed_tags or tag in self.void_tags:
            return
        if tag not in self.open_tags:
            return
        while self.open_tags:
            current = self.open_tags.pop()
            self.output.append(f"</{current}>")
            if current == tag:
                break

    def handle_data(self, data: str) -> None:
        if not self.skip_depth:
            self.output.append(html.escape(data, quote=False))

    def handle_entityref(self, name: str) -> None:
        if not self.skip_depth:
            self.output.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        if not self.skip_depth:
            self.output.append(f"&#{name};")

    def close(self) -> None:
        super().close()
        while self.open_tags:
            self.output.append(f"</{self.open_tags.pop()}>")

    def result(self) -> str:
        self.close()
        cleaned = "".join(self.output)
        return re.sub(r"\n{3,}", "\n\n", cleaned).strip()

    def _sanitize_attrs(self, tag: str, attrs: list[tuple[str, str | None]]) -> str:
        allowed = self.global_attrs | self.tag_attrs.get(tag, set())
        clean: list[tuple[str, str]] = []

        for raw_name, raw_value in attrs:
            if raw_value is None:
                continue
            name = raw_name.lower().strip()
            value = raw_value.strip()
            if name.startswith("on") or name not in allowed:
                continue
            if name == "style":
                value = self._sanitize_style(value)
                if not value:
                    continue
            elif name == "href":
                value = self._sanitize_url(value, allow_data=False)
                if not value:
                    continue
            elif name == "src":
                value = self._sanitize_url(value, allow_data=True)
                if not value:
                    continue
            elif name in {"width", "height", "colspan", "rowspan", "span"}:
                value = re.sub(r"[^0-9.%]", "", value)[:16]
                if not value:
                    continue
            else:
                value = re.sub(r"[\x00-\x1f\x7f]", "", value)[:500]

            clean.append((name, value))

        if tag == "a" and any(name == "href" for name, _ in clean):
            clean.append(("target", "_blank"))
            clean.append(("rel", "noopener noreferrer"))
        if tag == "img" and not any(name == "loading" for name, _ in clean):
            clean.append(("loading", "lazy"))

        return "".join(f' {name}="{html.escape(value, quote=True)}"' for name, value in clean)

    def _sanitize_style(self, style: str) -> str:
        if "expression" in style.lower() or "<" in style or ">" in style:
            return ""
        declarations: list[str] = []
        for part in style.split(";"):
            if ":" not in part:
                continue
            name, value = part.split(":", 1)
            name = name.strip().lower()
            value = value.strip()
            if name not in self.allowed_css:
                continue
            if re.search(r"url\s*\(|@import|javascript:|data:", value, re.IGNORECASE):
                continue
            value = re.sub(r"[\x00-\x1f\x7f]", "", value)[:240]
            if value:
                declarations.append(f"{name}: {value}")
        return "; ".join(declarations)

    def _sanitize_url(self, value: str, allow_data: bool) -> str:
        value = re.sub(r"[\x00-\x20\x7f]", "", html.unescape(value))
        lower = value.lower()
        if allow_data and lower.startswith(("data:image/png", "data:image/jpeg", "data:image/gif", "data:image/webp")):
            return value
        parsed = urlparse(value)
        if parsed.scheme in {"http", "https", "mailto", "tel"}:
            return value
        if not parsed.scheme and value.startswith("#"):
            return value
        return ""


def sanitize_html(raw_html: str) -> str:
    parser = HtmlSanitizer()
    parser.feed(raw_html)
    return parser.result()


def extract_text(raw_html: str) -> str:
    parser = TextExtractor()
    parser.feed(raw_html)
    return parser.text()


def clean_title(value: str, fallback_html: str) -> str:
    title = re.sub(r"\s+", " ", value or "").strip()
    if title:
        return title[:180]

    heading = re.search(r"<h[1-3][^>]*>(.*?)</h[1-3]>", fallback_html, flags=re.IGNORECASE | re.DOTALL)
    if heading:
        text = extract_text(heading.group(1))
        if text:
            return text[:180]
    return "Untitled article"


def escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def make_snippet(text: str, query: str, width: int = 220) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    if not text:
        return ""
    query = re.sub(r"\s+", " ", query or "").strip()
    if not query:
        return text[:width]

    index = text.lower().find(query.lower())
    if index < 0:
        return text[:width]

    padding = max(20, (width - len(query)) // 2)
    start = max(0, index - padding)
    end = min(len(text), index + len(query) + padding)
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(text) else ""
    return f"{prefix}{text[start:end]}{suffix}"


def match_field(row: sqlite3.Row, query: str) -> str:
    if not query:
        return ""
    needle = query.lower()
    if needle in (row["title"] or "").lower():
        return "title"
    if needle in (row["source_url"] or "").lower():
        return "source_url"
    if needle in (row["text_content"] or "").lower():
        return "body"
    return ""


def article_from_row(row: sqlite3.Row, include_html: bool = False, search_query: str = "") -> dict[str, Any]:
    text = row["text_content"] or ""
    field = match_field(row, search_query)
    item: dict[str, Any] = {
        "id": row["id"],
        "title": row["title"],
        "source_url": row["source_url"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "summary": make_snippet(text, search_query),
        "match_field": field,
    }
    if include_html:
        item["html"] = row["html"]
        item["text_content"] = text
    return item


class AppHandler(BaseHTTPRequestHandler):
    server_version = "ArticleOutliner/0.1"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/":
            self.serve_static(STATIC_DIR / "index.html")
            return
        if path == "/favicon.ico":
            self.send_response(204)
            self.send_common_headers("image/x-icon")
            self.end_headers()
            return
        if path in {"/app.js", "/style.css"}:
            self.serve_static(STATIC_DIR / path.lstrip("/"))
            return
        if path == "/api/articles":
            query = parse_qs(parsed.query).get("q", [""])[0]
            self.list_articles(query)
            return
        match = re.fullmatch(r"/api/articles/(\d+)", path)
        if match:
            self.get_article(int(match.group(1)))
            return
        self.respond_error(404, "Not found")

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/articles":
            self.create_article()
            return
        self.respond_error(404, "Not found")

    def do_DELETE(self) -> None:
        match = re.fullmatch(r"/api/articles/(\d+)", urlparse(self.path).path)
        if match:
            self.delete_article(int(match.group(1)))
            return
        self.respond_error(404, "Not found")

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_common_headers("text/plain; charset=utf-8")
        self.end_headers()

    def serve_static(self, path: Path) -> None:
        try:
            resolved = path.resolve()
            if not str(resolved).startswith(str(STATIC_DIR.resolve())) or not resolved.is_file():
                self.respond_error(404, "Not found")
                return
            body = resolved.read_bytes()
        except OSError:
            self.respond_error(404, "Not found")
            return

        content_type = mimetypes.guess_type(str(resolved))[0] or "application/octet-stream"
        if content_type.startswith("text/") or resolved.suffix == ".js":
            content_type += "; charset=utf-8"
        self.send_response(200)
        self.send_common_headers(content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def list_articles(self, query: str = "") -> None:
        query = re.sub(r"\s+", " ", query or "").strip()[:160]
        with connect_db() as conn:
            if query:
                pattern = f"%{escape_like(query)}%"
                rows = conn.execute(
                    """
                    SELECT id, title, source_url, html, text_content, created_at, updated_at
                    FROM articles
                    WHERE title LIKE ? ESCAPE '\\'
                       OR source_url LIKE ? ESCAPE '\\'
                       OR text_content LIKE ? ESCAPE '\\'
                    ORDER BY updated_at DESC
                    """,
                    (pattern, pattern, pattern),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT id, title, source_url, html, text_content, created_at, updated_at FROM articles ORDER BY updated_at DESC"
                ).fetchall()
        self.respond_json({"articles": [article_from_row(row, search_query=query) for row in rows], "query": query})

    def get_article(self, article_id: int) -> None:
        with connect_db() as conn:
            row = conn.execute(
                "SELECT id, title, source_url, html, text_content, created_at, updated_at FROM articles WHERE id = ?",
                (article_id,),
            ).fetchone()
        if row is None:
            self.respond_error(404, "Article not found")
            return
        self.respond_json({"article": article_from_row(row, include_html=True)})

    def create_article(self) -> None:
        try:
            payload = self.read_json()
        except ValueError as exc:
            self.respond_error(400, str(exc))
            return

        raw_html = str(payload.get("html") or "")
        if not raw_html.strip():
            self.respond_error(400, "HTML is required")
            return

        safe_html = sanitize_html(raw_html)
        if not safe_html:
            self.respond_error(400, "No readable HTML remained after sanitizing")
            return

        title = clean_title(str(payload.get("title") or ""), safe_html)
        source_url = str(payload.get("source_url") or "").strip()[:1000]
        text = extract_text(safe_html)
        timestamp = now_iso()

        with connect_db() as conn:
            cursor = conn.execute(
                """
                INSERT INTO articles (title, source_url, html, text_content, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (title, source_url, safe_html, text, timestamp, timestamp),
            )
            article_id = int(cursor.lastrowid)
            row = conn.execute(
                "SELECT id, title, source_url, html, text_content, created_at, updated_at FROM articles WHERE id = ?",
                (article_id,),
            ).fetchone()
            conn.commit()

        self.respond_json({"article": article_from_row(row, include_html=True)}, status=201)

    def delete_article(self, article_id: int) -> None:
        with connect_db() as conn:
            cursor = conn.execute("DELETE FROM articles WHERE id = ?", (article_id,))
            conn.commit()
        if cursor.rowcount == 0:
            self.respond_error(404, "Article not found")
            return
        self.respond_json({"ok": True})

    def read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            raise ValueError("Request body is required")
        if length > MAX_REQUEST_BYTES:
            raise ValueError("Request body is too large")
        body = self.rfile.read(length)
        try:
            payload = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError("Request body must be JSON") from exc
        if not isinstance(payload, dict):
            raise ValueError("Request body must be a JSON object")
        return payload

    def respond_json(self, payload: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_common_headers("application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def respond_error(self, status: int, message: str) -> None:
        self.respond_json({"error": message}, status=status)

    def send_common_headers(self, content_type: str) -> None:
        self.send_header("Content-Type", content_type)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "same-origin")
        self.send_header("Cache-Control", "no-store")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: http: https:; object-src 'none'; base-uri 'self'; frame-ancestors 'none'",
        )

    def log_message(self, fmt: str, *args: Any) -> None:
        timestamp = dt.datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {self.address_string()} {fmt % args}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Personal article outliner web app")
    parser.add_argument("--host", default=os.getenv("ARTICLE_OUTLINER_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("ARTICLE_OUTLINER_PORT", "8765")))
    parser.add_argument(
        "--allow-remote",
        action="store_true",
        help="Allow binding to a non-loopback host. Use only behind authentication and HTTPS.",
    )
    args = parser.parse_args()

    if not _remote_binding_allowed(args.host, args.allow_remote):
        raise SystemExit(
            "Refusing to bind to a non-loopback host without --allow-remote. "
            "This MVP has no authentication; keep it on 127.0.0.1 unless protected by another layer."
        )

    connect_db().close()
    server = ThreadingHTTPServer((args.host, args.port), AppHandler)
    print(f"Article Outliner running at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server")
    finally:
        server.server_close()


def _remote_binding_allowed(host: str, allow_remote: bool) -> bool:
    if allow_remote or os.getenv("ARTICLE_OUTLINER_ALLOW_REMOTE") == "1":
        return True
    normalized = host.strip().lower()
    return normalized in {"127.0.0.1", "localhost", "::1"}


if __name__ == "__main__":
    main()
