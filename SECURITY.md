# Security

Article Outliner is a private, personal-use clipping tool.

## Supported Use

- Run on `127.0.0.1` for local personal use.
- Store private clipping data in the local `data/articles.db` SQLite database.
- Commit only source code and documentation.

## Do Not Expose Directly

This MVP does not include:

- User accounts
- Login sessions
- Authorization checks
- CSRF tokens
- Rate limiting
- HTTPS termination

Do not bind it to a public interface or deploy it on the open internet unless you add authentication, HTTPS, and deployment hardening in front of it.

## Clipped HTML

The server sanitizes saved HTML before storage. It removes scripts, event handlers, unsafe URLs, forms, iframes, embeds, SVG, canvas, audio, and video. Sanitization reduces risk, but saved clips should still be treated as untrusted content.

## Bookmarklet Clip Endpoint

The bookmarklet uses `POST /api/clip` and a locally generated `X-Article-Outliner-Key`. CORS is enabled only for this clip endpoint, not for the article-reading API. Treat the bookmarklet URL as private because it contains the local clip key.

## Web Collection

`POST /api/web-collect` fetches search results and result pages from the server. Keep the app local, collect only content you are allowed to save, and do not publish copied article databases unless you have redistribution rights.

## Summaries

Article summaries are generated locally from stored body text. No clipping content is sent to an external summarization service by this project.

## Private Data

`data/` is ignored by git because article content may include personal browsing history, private URLs, copied copyrighted material, or sensitive text. Do not publish this directory.
