# Changelog

## 0.1.0

First release.

- `Trace`: one board in a normalized shape (room, seats, posts, artifacts, per-seat ops, source).
- Loaders for the SharedNet formats: share link or token, saved share JSON, `room export` NDJSON, episode directory.
- `analysis.v1`: the record format, with `validate()`.
- `regex_v1`: the reference annotator for the ten modes (R1 R2 REP, B1 B2, D1 D2 D3 D4 HB).
- `commsfail` CLI: `analyse`, `annotators`, `loaders`, `schema`, `validate`.
- Plugin discovery through the `commsfail.annotators` and `commsfail.loaders` entry-point groups, resolved lazily; a broken plugin is skipped with a warning.
- `examples/plugin`: a complete plugin with one annotator and one loader.
