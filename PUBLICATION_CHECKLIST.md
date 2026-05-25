# Publication Checklist

Use this checklist before pushing the repository to a public host.

## Required Checks

```powershell
python -m py_compile server.py
git status --short --ignored
git check-ignore -v data/articles.db data/clip_key.txt __pycache__/server.cpython-314.pyc
```

Expected result:

- `server.py` compiles.
- `data/` and `__pycache__/` are ignored.
- Only source files and documentation are staged or committed.

## Files That Must Not Be Published

- `data/`
- `__pycache__/`
- `data/clip_key.txt`
- `.env`
- `.env.*`
- `*.log`
- Local virtual environments
- Browser or editor metadata

## Remote Access

The app defaults to `127.0.0.1`. Non-loopback binding is blocked unless `--allow-remote` or `ARTICLE_OUTLINER_ALLOW_REMOTE=1` is used.

Do not use remote binding for a public deployment until authentication and HTTPS are added.

## Content Rights

This app is intended for private personal clipping. Do not publish saved article databases or copied article content unless you have the right to redistribute that content.

## License

The repository includes an MIT `LICENSE`. Confirm that this is still the intended license before major releases.
