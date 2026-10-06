# Changelog

## 0.2.0

The repository is now organised for many annotators from many people.

- `commsfail/sources/sharednet.py` holds everything about SharedNet. New: the `goal run` record folder is the
  default input (episode, room, checks, wakes, and each seat's Codex or Claude Code log as ops); a bare
  `room.ndjson`; tools `agent_posts`, `posts_by`, `commands`, `cites`, `mentions`, `view_at`, `summary`.
- One folder per annotator: `__init__.py`, `schema.json`, `README.md`. A folder registers itself.
- Each annotator owns its output schema (JSON Schema 2020-12). Every output goes in one envelope,
  `commsfail/record.v1`. `commsfail validate` checks the envelope and the output.
- The contract tests run on every annotator, built in or plugin, and on every sample in `tests/fixtures/`:
  conformance, determinism, no change to the trace, no network, real post numbers, no tokens.
- `commsfail new <name>` starts an annotator from the template. `commsfail trace` shows what a source holds.
- `regex_v1` 0.2.0: skips the goal post and the runner's reports. Its output on shares is unchanged.
- The source entry-point group is `commsfail.sources` (was `commsfail.loaders`). `--source` replaces `--loader`.
- New dependency: `jsonschema`.

## 0.1.0

First release.

- `Trace`: one board in a normalized shape (room, seats, posts, artifacts, per-seat ops, source).
- Loaders for the SharedNet formats: share link or token, saved share JSON, `room export` NDJSON, episode directory.
- `analysis.v1`: the record format, with `validate()`.
- `regex_v1`: the reference annotator for the ten modes (R1 R2 REP, B1 B2, D1 D2 D3 D4 HB).
- `commsfail` CLI: `analyse`, `annotators`, `loaders`, `schema`, `validate`.
- Plugin discovery through the `commsfail.annotators` and `commsfail.loaders` entry-point groups, resolved lazily; a broken plugin is skipped with a warning.
- `examples/plugin`: a complete plugin with one annotator and one loader.
