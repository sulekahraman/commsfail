# commsfail

Communication-failure analysis for multi-agent message boards.

When several agents work through one shared log, much of what goes wrong is visible in the log and in the agents' own records: a claim nobody read, an ask nobody answered, a review of work that was never delivered, a "tests pass" that the agent's own log contradicts. `commsfail` reads one board into a `Trace`, runs an **annotator** over it, and writes a **record**: the annotator's output, in the annotator's own schema, inside one common envelope.

The default input is a SharedNet trace. Anyone can contribute an annotator: a set of rules, a model as judge, a classifier, an importer of human labels. Each annotator decides what it reports and states it as a JSON Schema.

## Install

```bash
pip install git+https://github.com/xisen-w/commsfail
```

Python 3.10 or newer. One dependency: `jsonschema`.

## Use

```bash
commsfail trace runs/rom_abc                       # what the source holds: posts, seats, ops, checks
commsfail analyse runs/rom_abc --markdown          # the default annotator, regex_v1, as a short table
commsfail analyse runs/rom_abc -o record.json      # the full record
commsfail analyse runs/rom_abc --annotator my_v1   # another annotator
commsfail validate record.json                     # the output against its annotator's schema
commsfail annotators                               # every annotator, built in and plugins, with its schema id
commsfail schema regex_v1                          # an annotator's output schema
```

```python
from commsfail import load, run, validate_record

trace = load("runs/rom_abc")
record = run("regex_v1", trace)
assert validate_record(record) == []
print(record["output"]["metrics"])
```

## Input: SharedNet traces

`commsfail.sources.sharednet` reads every SharedNet source into the same `Trace`. A source shows what it has. A field it cannot show stays empty.

| source | made by | what it shows |
|---|---|---|
| record folder | `sharednet goal run --out DIR` | posts, seats, checks, wakes, each seat's own harness log, the episode summary |
| goal-export folder | `sharednet goal watch`, `sharednet goal export` | posts, the episode summary, sometimes checks |
| `room.ndjson` file | one file of a record | posts and seats |
| share JSON or share link | a share page | posts and seats; no ids, no artifacts, no ops |

A record folder holds these files. `commsfail` reads all of them except the workspace history and the agents' homes.

| file | what it holds |
|---|---|
| `episode.json` | the goal, the end conditions, `ended_by`, each agent's turns and tokens, the totals |
| `room.ndjson` | every message in the Room, in order |
| `checks.ndjson` | every check: when, why, the exit code, the output |
| `wakes.ndjson` | every turn: which seat, woken by what, the messages it was handed, the tokens |
| `agents/<seat>/turn-NNN.jsonl` | each turn's raw stream from the harness (Codex and Claude Code are parsed into ops) |

The `Trace`:

```
room       {id, name, created_at, latest_sequence, state}
seats      [{handle, label, driver, model, joined_at, principal, member_id}]
posts      [{seq, who, text, created_at, reply_to, type, role}]     role: goal | agent | runner | other | None
artifacts  [{id, by, created_at, name, sha256}]
ops        {seat: [{turn, i, kind, command, exit_code, output, paths, query, name, text}]}
checks     [{at, trigger, command, cause, exit_code, passed, sequence, output}]
wakes      [{seat, turn, fired, from, through, messages, started_at, ended_at, exit_code, failed, tokens}]
episode    the run's own summary
source     {kind, path or redacted token, room_id, loaded_at}
```

Tools in `commsfail.sources.sharednet` for annotators: `agent_posts`, `posts_by`, `commands`, `cites` (the `#n` a text cites), `mentions` (the `@names` it addresses), `view_at(trace, seq)` (the board as one seat could see it right after post `seq`), `summary`, `redact`, `parse_ts`.

Another format is a **source plugin**: a function from a path to a `Trace`, announced by an entry point (see [examples/plugin](examples/plugin)).

## Output: a record

```json
{
  "record": "commsfail/record.v1",
  "annotator": {"name": "regex_v1", "version": "0.2.0", "schema": "comms-failure/analysis.v1"},
  "source": {"kind": "goal-run", "path": "runs/rom_abc", "room_id": "rom_abc", "loaded_at": "..."},
  "output": {"...": "whatever the annotator's schema describes"}
}
```

The envelope is the same for every annotator. The `output` is the annotator's own. `validate` checks both.

## Annotators

| annotator | output schema | what it reports |
|---|---|---|
| [`regex_v1`](commsfail/annotators/regex_v1) | `comms-failure/analysis.v1` | the ten failure modes below, from text patterns; the reference |
| yours | yours | see the next section |

The ten modes of `regex_v1` come from our taxonomy of communication failures. A new annotator may use them (`commsfail.annotators.taxonomy` has the helpers), refine them, or report something else entirely.

| id | mode | what happened to the message |
|---|---|---|
| R1 | Open-set decay | not read: a seat re-claims or re-does an item an earlier post settled |
| R2 | Replacement re-does work | not read: a late joiner redoes what the log already holds |
| REP | Step repetition | not read: the same post, again |
| B1 | Belief without commitment | not binding: a hedged claim, or an ask nobody answered |
| B2 | Identity drift | not binding: who speaks, or who leads, changes under one handle |
| D1 | Unattested action | never done: "pushed", "uploaded", "tests pass" with no proof in the record |
| D2 | Review of nothing | never done: a review passed on an item never delivered |
| D3 | Closure before budget | never done: the board ends in a pause, an open ask or a heartbeat, with items open |
| D4 | Capability not routed | never done: a request for an action only another seat can take, left there |
| HB | Heartbeat cost | never done: status posts with no new information |

## Contributing an annotator

Different people bring different methods. All of them live side by side here, and the same tests check all of them. You do not need anyone's permission to design a new kind of annotator. You need to follow the rules below.

### The rules

Every annotator, built in or plugin, must obey these. `tests/test_contract.py` checks each one, on every annotator and on every sample in `tests/fixtures/`.

1. **One folder, three files.** `commsfail/annotators/<name>/` holds `__init__.py` (the code, which sets `ANNOTATOR = <the class>`), `schema.json` (the output schema) and `README.md` (what it reports, how, what it is good and bad at). The folder name is the annotator's `name`.
2. **Name and version.** `name` is lowercase letters, digits and `_`, for example `judge_gpt_v1`. Change `version` whenever the output for the same trace changes.
3. **Your output, your schema.** `schema.json` is a JSON Schema (draft 2020-12) with `$schema`, `$id`, `title` and `description`. The `$id` names your output format, for example `commsfail/judge_gpt_v1/v1`. Change the `$id` when the format changes. Every output must validate against it.
4. **Same trace, same output.** `annotate()` is deterministic and does not change the trace. A model judge fixes its model, temperature and seed, or caches its answers, so that a record can be made again.
5. **No network in `annotate()`.** Loading is the source's job. A model judge gets its answers in a separate step and saves them, for example one JSON file per trace in its own folder; `annotate()` reads the saved answers. Save the answers for the samples too, so the tests can run. The tests cut the network.
6. **Point at real posts.** Any object in your output with an integer `seq` must name a post that exists, or 0 for the whole Room.
7. **No secrets.** Pass every excerpt of post text through `redact()`. No token may appear in the output.
8. **Blind to the outcome.** An annotator never reads the task's grade or the experimental condition. It judges the conversation, not the result.
9. **Say what you are not sure of.** When the source cannot show what you report, say so in the output (for example `"severity": "unknown"`) instead of a guess.

### Steps

```bash
git clone https://github.com/xisen-w/commsfail && cd commsfail
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]" -e examples/plugin
pytest                                     # all green before you start

git checkout -b annotator/<name>
commsfail new <name>                       # makes the folder from the template, and tests/annotators/test_<name>.py
```

Then:

1. Write your method in `commsfail/annotators/<name>/__init__.py`. Start from `commsfail.sources.sharednet` for the tools, and from `commsfail.annotators.taxonomy` if you report the ten modes.
2. Describe your output in `schema.json`. Make it strict: `required` and `additionalProperties: false` where you can. A loose schema checks nothing.
3. Fill in `README.md`: what it reports, how, good at, weak at, and which traces you read by hand to check it.
4. Write behaviour tests in `tests/annotators/test_<name>.py`: which posts it points at on the samples, and why.
5. Run `pytest`, then `commsfail analyse tests/fixtures/goal_run --annotator <name>` and read the output yourself.
6. Open a pull request.

### Or keep it in your own repository

If your method lives next to other code, for example a training codebase, make it a plugin. Copy [examples/plugin](examples/plugin), set the entry point, and ship `schema.json` as package data:

```toml
[project.entry-points."commsfail.annotators"]
my_v1 = "my_package.annotators:MyV1"
```

When your package and `commsfail` are installed together, `commsfail annotators` lists it and `pytest` in this repository runs the contract on it.

### What a reviewer checks

- The contract tests pass on all samples, on Python 3.10 to 3.13.
- The folder has the three files, and the README is honest about weak cases.
- The schema is strict and its `$id` is new, or the version of an existing `$id` is unchanged in meaning.
- The behaviour tests name posts and reasons, not only "it runs".
- No real Room content, no token and no share link in the code, the tests or the PR text.
- The PR changes only its own folder and its own test, unless it says why.

### Adding a sample

The samples in `tests/fixtures/` are the shared ground for every annotator. To add one, put a record folder (or a share `.json`, or a `.ndjson`) there and describe it in [tests/fixtures/README.md](tests/fixtures/README.md). Use synthetic content, or content from a Room whose people agreed. The contract tests then run every annotator on it.

### Changing shared code

`sources/`, `annotators/base.py`, `annotators/taxonomy.py`, the record envelope and the CLI are shared. Open an issue first. A change to the envelope is a new `record` version.

### Data rules

- No real Room content in tests, examples or issues unless the people in the Room agreed.
- Never commit a token, a key or a share link. A share link is a capability: whoever holds it can read the Room. Cite a Room by name.
- Records of experiments stay where the experiment keeps its data. This repository holds code and synthetic samples only.

## Repository layout

```
commsfail/
  trace.py                 the Trace
  sources/
    sharednet.py           everything about SharedNet: the readers and the tools
  annotators/
    base.py                the contract: schema loading, validation, the record envelope
    taxonomy.py            the ten modes and helpers, for annotators that use them
    regex_v1/              one annotator: __init__.py, schema.json, README.md
    _template/             what `commsfail new` copies
  cli.py
tests/
  fixtures/goal_run/       a synthetic goal-run record folder
  fixtures/share.json      a synthetic share
  test_contract.py         the rules, on every annotator and every sample
  annotators/              one behaviour test file per annotator
examples/plugin/           an annotator and a source in a separate package
```

## License

MIT.
