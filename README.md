# Article Outliner

Personal-use web app for saving rich web-article clips on a server and reading them with collapsible outline sections.

This project is designed for private clipping and reading. It is not a public publishing platform and it does not include user accounts or authentication.

## Run

```powershell
python server.py --host 127.0.0.1 --port 8765
```

Open `http://127.0.0.1:8765`.

## MVP Scope

- Paste rich HTML copied from a browser.
- Save sanitized article HTML to server-side SQLite.
- List, search, open, and delete saved articles.
- Search covers title, source URL, and stored body text across unopened articles.
- Collapse or expand heading sections.
- Run with Python standard library only.

## Storage

Articles are stored in `data/articles.db`.

`data/` is ignored by git because saved article content may contain personal browsing history, copied third-party material, private URLs, and other sensitive text. Do not commit it.

## Security Notes

The server sanitizes saved HTML and removes scripts, event handlers, unsafe URLs, forms, iframes, embeds, SVG, canvas, audio, and video.

This first version has no login, no permissions, and no CSRF protection beyond the local-only default. Keep it bound to `127.0.0.1` unless it is placed behind authentication and transport security. Binding to a non-loopback host requires an explicit `--allow-remote` flag or `ARTICLE_OUTLINER_ALLOW_REMOTE=1`.

## Publish Safety

Before publishing a repository, run:

```powershell
git status --short --ignored
git check-ignore -v data/articles.db __pycache__/server.cpython-314.pyc
```

Only source files and documentation should be committed. Do not publish `data/`, `__pycache__/`, local environment files, or logs.

## License

No open-source license has been selected yet. Add a `LICENSE` file before inviting reuse or contributions.
