# Contributing

## Setup

```bash
git clone https://github.com/xisen-w/commsfail.git && cd commsfail
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]" -e examples/plugin
pytest                      # green before you touch anything; the example plugin is under test too
commsfail annotators
```

## Two ways to add an annotator

1. **As a plugin in your own repository.** Copy `examples/plugin`, rename the package, set `name` on the class and the two entry points. Nothing needs to be merged here. When your package and this one are installed together, `commsfail annotators` lists it and the contract tests run on it.
2. **In this repository**, when the annotator is general enough to ship with the package: a file in `commsfail/annotators/`, one line in `BUILTIN`, a `tests/test_<name>.py` with at least one behaviour test on `synthetic_trace` (see `tests/conftest.py`), and a PR description that says what it is good at and what it is not.

## The contract

`tests/test_contract.py` runs on every registered annotator. It enforces, and this is why:

- **Every mode id is present in `modes`**, even when absent, so records line up column for column across annotators.
- **Confidence is per mode.** When the source cannot show a mode (a share has no artifact rows, so D1 cannot be verified), report `severity: "unknown"` rather than a number.
- **Evidence is `{seq, who, excerpt, why}`**, at most 25 rows per mode, every `seq` a post that exists, the excerpt redacted (`redact()` in `regex_v1` strips URLs, emails and tokens). The `why` is the sentence a reader would write in the margin.
- **`annotate()` is deterministic and offline.** Loading is the loader's job. A record must be recomputable from the saved trace.
- **A model-as-judge annotator records the model and the prompt hash in `source`** and never sees an outcome grade or an experimental condition.

## Changing the taxonomy

The mode ids are the schema. Adding, removing or renaming one is `analysis.v2`: open an issue first. The change then moves `commsfail/schema.py` (`MODES`), the reference annotator, the README table and `tests/conftest.py` together in one PR.

## Data rules

- **Synthetic fixtures only.** No real board content in tests, examples or issues. If a bug needs a real transcript, describe the pattern and reproduce it in `synthetic_trace`.
- **Never commit a token, a key or a share link.** A share link is a capability: whoever holds it can read the Room. Cite a board by name.
- **The CLI's only network call is the share-link loader.** `annotate()` must not call out.

## Pull requests

Branch from `main`; one change per branch. Tests must be green on Python 3.10 to 3.13 (CI runs them). Commit subject in the imperative, body says why. Squash-merge.
