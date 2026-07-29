
# Development

This document collects the commands used to develop, test, document, and release `minspp`.

## Setup

The project is managed with [uv](https://docs.astral.sh/uv/), install it and sync the environment
(the `dev` and `docs` dependency groups are both installed by default):

```bash
$ curl -LsSf https://astral.sh/uv/install.sh | sh
$ uv python install
$ uv sync
```

All the commands below assume this step was done.

## Run Tests

```bash
$ uv run pytest -v
```

## Run Linter

CI requires a perfect 10.00 score:

```bash
$ uv run pylint ./minspp --fail-under=10
```

## Build Docs

```bash
$ cd docs
$ uv run sphinx-apidoc -o source/ ../minspp --force --module-first --separate
$ cd source && uv run sphinx-build -b html . _build
```

Open `docs/source/_build/index.html`.

## Release

Bump `version` in `pyproject.toml`, then tag and push (the tag must be strictly greater than the
version currently on PyPI, otherwise the release workflow refuses to publish):

```bash
$ git commit -a -m "Release 0.0.1"
$ git tag 0.0.1
$ git push origin master
$ git push origin 0.0.1
```
