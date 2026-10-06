# Contributing

The kit is small on purpose: plain Python scripts an AI agent runs, and Markdown instructions it follows.
Fixes and improvements are welcome, from people and from their agents.

## What lives where

- `kit/`: the scripts. Each one does its work in `main()`, so importing it runs nothing (`tests/test_scripts.py`
  checks this). Shared helpers are in `kit/common.py`.
- `AGENTS.md`, `SETUP.md`, `workflows/`: the agent's instructions. When a script's behavior changes, the line that
  tells the agent about it usually changes too.
- `templates/`: the blank `my-search/` files a new user starts from.
- `examples/demo/`: Robin Sample, a fictional user, for the tests and the README.
- `tests/`: plain `unittest`, no extra libraries.

## Before a pull request

```
python3 -m pip install -r requirements.txt
python3 -m unittest discover -s tests       # the PDF tests need Chrome (or CHROME_PATH); without it they're skipped
ruff check && ruff format --check           # pip install ruff
```

CI runs the same on Linux (Python 3.9 and 3.13) and macOS. Python 3.9 is the oldest supported version,
so no `match` and no `X | None` in annotations.

- A fixed bug gets a test that fails without the fix.
- The tests run offline: fake the network the way `tests/test_sources.py` does.
  LinkedIn's real pages are checked separately by `tests/test_live.py`, once a week in CI
  (`.github/workflows/live.yml`), or by hand: `JOBKIT_LIVE=1 python3 -m unittest discover -s tests -p test_live.py -v`
- Add a line to `CHANGELOG.md` under "Unreleased" (start that section if it isn't there).
- Nothing from `my-search/` and no real person's data, in code, tests or examples. Use Robin Sample.

## The rules the code keeps

These are the point of the kit. A change that weakens one needs a very good reason, said in the pull request:

- A CV, cover letter or form answer says only what the user's `profile.yaml` says. `build.py` refuses anything
  else (an unknown bullet, a new number, a banned phrase). Fix the spec; never loosen a check to make one pass.
- A PDF a company already received is never overwritten.
- Nothing is sent, submitted or ticked (a message, a form, a consent box) without the user.
- LinkedIn is used at a low, human pace.

## Versions and releases

Versions are `MAJOR.MINOR.PATCH`, counted from the user's side:

- **MAJOR**: updating needs a change to the user's `my-search/` files (a renamed field, a new required file).
  The changelog says exactly what to change.
- **MINOR**: something new; existing `my-search/` files keep working as they are.
- **PATCH**: fixes only.

To release: in `CHANGELOG.md`, rename "Unreleased" to the version and date, and merge. Then on GitHub:
Releases > Draft a new release > a new tag `vX.Y.Z` on `main`, with that changelog section as the notes.
