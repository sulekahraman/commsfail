# Contributing

The guide is in the README: [Contributing an annotator](README.md#contributing-an-annotator).

In short: one folder per annotator in `commsfail/annotators/<name>/` with the code, its own `schema.json` and a `README.md`; start it with `commsfail new <name>`; `pytest` checks the rules on every annotator and every sample; open a pull request from a branch named `annotator/<name>`.
