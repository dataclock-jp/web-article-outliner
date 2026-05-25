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

## Private Data

`data/` is ignored by git because article content may include personal browsing history, private URLs, copied copyrighted material, or sensitive text. Do not publish this directory.
