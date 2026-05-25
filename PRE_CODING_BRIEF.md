# Pre-Coding Brief

## Purpose

Build a personal-use web app that stores clipped web articles on a server and lets the user read them in a preserved visual form while collapsing or expanding sections like an outliner.

## Target User

Single personal user. The first version is optimized for private self-hosted use, not public sharing or team collaboration.

## Use Cases

- Paste rich HTML copied from a web article into the app and save it on the server.
- Reopen saved articles from another browser session through the web app.
- Collapse and expand the entire article or individual heading sections.
- Search saved article titles, source URLs, and stored body text, including articles that are not currently open.
- Save the article currently open in another browser tab through a bookmarklet.
- Enter a web collection keyword, choose strict or fuzzy search, and automatically save the top N result pages.

## Functional Requirements And Acceptance Criteria

- Save article snapshots.
  - Acceptance: `POST /api/articles` with title, optional URL, and HTML returns an article id.
  - Acceptance: `GET /api/articles/{id}` returns the saved article after server restart.
- Preserve readable visual structure.
  - Acceptance: pasted HTML is stored as sanitized HTML, not plain text only.
  - Acceptance: common elements such as headings, paragraphs, links, lists, images, blockquotes, pre/code, tables, bold, and italic remain visible.
- Collapse and expand article sections.
  - Acceptance: headings become collapsible section controls in the article reader.
  - Acceptance: the UI has expand-all and collapse-all controls.
- Store data server-side.
  - Acceptance: article records persist in `data/articles.db`.
- Search across saved body text.
  - Acceptance: `GET /api/articles?q=<term>` returns matches from title, source URL, or `text_content`.
  - Acceptance: search results include a body snippet when the match is found inside an unopened article.
- Save the current browser article.
  - Acceptance: `GET /api/bookmarklet` returns a bookmarklet URL that posts to the local app.
  - Acceptance: `POST /api/clip` stores title, source URL, and HTML when `X-Article-Outliner-Key` matches the local clip key.
  - Acceptance: `POST /api/clip` returns 403 when the clip key is missing or invalid.
- Collect pages from web search.
  - Acceptance: `POST /api/web-collect` with `{ "keyword": string, "count": number, "mode": "exact" | "fuzzy" }` searches the web and attempts to save the top results.
  - Acceptance: exact mode searches for the quoted phrase; fuzzy mode searches the unquoted keyword.
  - Acceptance: the response reports imported, skipped, and failed URLs separately.
- Keep the app dependency-light.
  - Acceptance: it runs with the Python standard library only.
- Keep the repository publish-safe.
  - Acceptance: runtime article data and Python cache files are ignored by git.
  - Acceptance: README and security notes clearly state that this MVP has no authentication and must not be exposed publicly.
  - Acceptance: non-loopback host binding requires an explicit `--allow-remote` flag or environment override.

## Explicit Out Of Scope

- No browser extension in the first version.
- No multi-user accounts, synchronization, public sharing, or permission management.
- No saved third-party page scripts are executed in the reader.
- No automatic background monitoring of browser tabs.
- No guarantee that every search result can be fetched; pages may block automated access or return unsupported content.
- No exact reproduction of interactive pages, ads, videos, login-only content, or site-specific dynamic behavior.
- No changes to existing directories under `D:\CodexProject` except `D:\CodexProject\web-article-outliner`.

## Interface Contracts

- `GET /` serves the web UI.
- `GET /style.css` serves styles.
- `GET /app.js` serves client logic.
- `GET /api/articles` returns a JSON list of saved articles.
- `GET /api/articles?q=<term>` returns only articles matching title, source URL, or stored body text.
- `POST /api/articles` accepts JSON: `{ "title": string, "source_url": string, "html": string }`.
- `GET /api/bookmarklet` returns JSON: `{ "bookmarklet": string, "label": string }`.
- `POST /api/clip` accepts the same JSON as `/api/articles`, but requires `X-Article-Outliner-Key`.
- `POST /api/web-collect` accepts JSON: `{ "keyword": string, "count": number, "mode": "exact" | "fuzzy" }`.
- `GET /api/articles/{id}` returns one article JSON object.
- `DELETE /api/articles/{id}` deletes one article.

## Constraints And Quality Bars

- Runtime: Python 3 with only the standard library.
- Storage: SQLite database under `data/articles.db`.
- Security: sanitize clipped HTML on the server; remove scripts, event handlers, inline JavaScript URLs, forms, iframes, embeds, and unsafe style attributes.
- Personal-use assumption: bind to `127.0.0.1` by default.

## Repository Baseline

- Workspace root: `D:\CodexProject`.
- Baseline state: `D:\CodexProject` is not a git repository.
- New project path: `D:\CodexProject\web-article-outliner`.
- Existing projects are read-only and out of scope.

## Existing-Code Survey And Identifier Pre-Grep

There is no existing codebase for this app. The first version will create standalone files inside `D:\CodexProject\web-article-outliner`.

## Change Boundary

Write-target files:

- `D:\CodexProject\web-article-outliner\PRE_CODING_BRIEF.md`
- `D:\CodexProject\web-article-outliner\.gitignore`
- `D:\CodexProject\web-article-outliner\README.md`
- `D:\CodexProject\web-article-outliner\SECURITY.md`
- `D:\CodexProject\web-article-outliner\PUBLICATION_CHECKLIST.md`
- `D:\CodexProject\web-article-outliner\server.py`
- `D:\CodexProject\web-article-outliner\static\index.html`
- `D:\CodexProject\web-article-outliner\static\style.css`
- `D:\CodexProject\web-article-outliner\static\app.js`

Runtime-generated files:

- `D:\CodexProject\web-article-outliner\data\articles.db`

Off-limits:

- All other directories under `D:\CodexProject`.
- The source guideline HTML under `D:\ClaudeProject`.

## Verification Plan

Smoke checks:

- `python -m py_compile server.py`
- Start `python server.py --host 127.0.0.1 --port 8765`
- `GET http://127.0.0.1:8765/` returns the UI.
- `POST http://127.0.0.1:8765/api/articles` stores a sample article.
- `GET http://127.0.0.1:8765/api/articles` lists the sample article.
- `GET http://127.0.0.1:8765/api/articles?q=<body-term>` finds the sample article by body text.
- `GET http://127.0.0.1:8765/api/bookmarklet` returns a `javascript:` URL.
- `POST http://127.0.0.1:8765/api/clip` without a key returns 403.
- `POST http://127.0.0.1:8765/api/web-collect` with a small count returns imported/skipped/failed arrays.
- `git check-ignore -v data/articles.db __pycache__/server.cpython-314.pyc` confirms runtime files are ignored.
- `python server.py --host 0.0.0.0 --port 8765` exits unless `--allow-remote` is passed.

Definition of done:

- The smoke checks pass.
- The local server is running and the user has a URL to open.
