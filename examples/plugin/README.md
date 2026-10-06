# commsfail example plugin

A complete plugin: one annotator (`example_v1`) and one loader (`chat_jsonl`), announced through the two entry points in `pyproject.toml`.

```bash
pip install -e .                                   # with commsfail installed
commsfail annotators                               # example_v1 appears, with where it comes from
commsfail loaders                                  # chat_jsonl appears
commsfail analyse sample_chat.jsonl --loader chat_jsonl --annotator example_v1 --markdown
commsfail analyse sample_chat.jsonl --loader chat_jsonl --markdown      # the reference annotator on the same trace
```

To make your own: copy this directory, rename the package, set `name` on the class and the two entry points, and replace the body of `annotate()`. Keep it offline and deterministic. When your package and `commsfail` are installed together, the contract tests in the main repository run on your annotator too.
