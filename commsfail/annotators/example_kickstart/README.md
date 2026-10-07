# example_kickstart

<!-- kickstart -->
> **Start here.** This annotator is a working sample that you copy. `commsfail new <name>` makes `commsfail/annotators/<name>/` from this folder, and `tests/annotators/test_<name>.py` from its test. The copy runs and passes its tests at once. Then you replace the method, the taxonomy and the expectations with yours, one file at a time:
>
> 1. `taxonomy.json`: your failure modes. Give each one an id, a name, a definition a person can label with, and optionally a group. In `maps_to`, say which regex_v1 mode it corresponds to, if one does. Your taxonomy may cut failures differently from anyone else's; `maps_to` is what keeps the results comparable.
> 2. `__init__.py`: your method in `annotate()`, and `modes_in()`, which returns the mode ids an output reports.
> 3. `schema.json`: your output. Keep the mode names in step with `taxonomy.json`.
> 4. This README: fill in every section below.
> 5. `tests/annotators/test_<name>.py`: which posts your method points at on the samples, and why.
>
> Your taxonomy is also a codebook for human labels: `commsfail audit export ... --codebook <name>`.
<!-- /kickstart -->

Open questions and bare claims: a two-mode sample taxonomy. Replace this sentence with what your annotator reports.

**Output:** [schema.json](schema.json). For each post it points at: the post, the seat, the mode from [taxonomy.json](taxonomy.json), a redacted excerpt, and why. It also gives the number of posts and the count per mode.

**Taxonomy:** [taxonomy.json](taxonomy.json), with two modes.
- `open_question` (maps to regex_v1's B1): a question that no later post answers or cites.
- `bare_claim` (maps to regex_v1's D1): "done" or "passes", with no file, item or post number a reader could check.

**How:** text rules over the agent posts. A question is a post that ends in "?". It counts as answered when a later post replies to it or cites its number. A bare claim is a done or pass word in a post that names nothing checkable: no backticked item, no file name, no `#n`.

**Good at:** short boards where questions end in "?" and where claims name what they are about.

**Weak at:** a question asked without "?"; an answer that neither replies nor cites; a claim that names a file but is still false, which needs the seat's own log (see facts_v1).

**Checked on:** the samples in `tests/fixtures/` and the synthetic board in `tests/conftest.py`, read by hand.
