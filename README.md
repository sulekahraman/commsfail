# commsfail

Communication-failure analysis for multi-agent message boards.

When several language-model agents work through one shared log, a SharedNet Room, a group chat, a shared forum, most of what goes wrong is visible in the log itself: a claim nobody read, an ask nobody answered, a review of work that was never delivered, a Room that ends in heartbeats. `commsfail` reads one board into a `Trace`, runs an annotator over it and writes one `analysis.v1` record: room-level metrics, the work items that were claimed, done and reviewed, and one entry per failure mode with severity, confidence and the posts it was read from.

A record is a pointer for a human reader, not a label. Every number in it comes with the evidence it was computed from.

## Install

```bash
pip install git+https://github.com/xisen-w/commsfail
```

Python 3.10 or newer. The core has no dependencies.

## In thirty seconds

```bash
commsfail analyse room.ndjson --markdown      # a `sharednet room export`
commsfail analyse share.json -o out.json      # a saved SharedNet share
commsfail analyse <share link>                # the only call that touches the network
commsfail validate out.json
commsfail annotators                          # what is registered, built in and plugins
commsfail loaders
commsfail schema                              # the analysis.v1 fields
```

## In Python

```python
from commsfail import load_trace, get_annotator, validate

trace = load_trace("room.ndjson")
record = get_annotator("regex_v1").annotate(trace)
assert validate(record) == []
for mode in record["modes"]:
    if mode["present"]:
        print(mode["id"], mode["severity"], mode["count"], mode["evidence"][0]["why"])
```

## The failure modes

Ten modes in three groups. The groups say what happened to the message; the last column says which layer of a structured board removes the mode, or that none does.

| id | mode | the message was | removed by |
|---|---|---|---|
| R1 | Open-set decay | not read: a seat re-claims or re-does an item that an earlier post already settled | view |
| R2 | Replacement re-does work | not read: a late joiner redoes what the log already holds | view |
| REP | Step repetition | not read: the same post, again | view |
| B1 | Belief without commitment | not binding: a hedged claim, or an ask nobody answered, that others acted on | naming |
| B2 | Identity drift | not binding: who is speaking, or who is in charge, changes under the same handle | check |
| D1 | Unattested action | never done: "paid", "pushed", "uploaded" with no receipt the record can show | check |
| D2 | Review of nothing | never done: a review passed on an item that was never delivered | check |
| D3 | Closure before budget | never done: the board ends in a pause, an open ask or a heartbeat, with items still open | none |
| D4 | Capability not routed | never done: a request for an action only another seat (or a human) can take, left there | none |
| HB | Heartbeat cost | never done: status posts that carry no new information | none |

Layers: **naming** gives claims and asks an id so they can be answered or refused; **view** shows each seat a projection of the log instead of the whole log; **check** makes an action carry a receipt. A mode marked **none** needs a human or a budget.

## The record

```
schema       "comms-failure/analysis.v1"
source       kind (share | share-file | export | episode | yours), path or redacted token, fetched_at, annotator "name@version"
room         name, created_at, latest_sequence, seats [{handle, label, driver, joined_at, principal}]
metrics      posts, seats, asks, asks_unanswered, claims, re_claims, heartbeat_posts, heartbeat_share,
             open_items_at_end, last_post_kind, and whatever else the annotator counts
items        {item: {claims[], done[], review[], upload[], status_at_end}} for every work item found in the text
modes        one entry per mode id: present, severity none|low|medium|high|unknown, count, confidence 0..1,
             removed_by, evidence [{seq, who, excerpt, why}]
annotation   empty slots for human labels (accept, result, review_pass) and facts (delivered, acted, passed)
caveats      what this source cannot show
```

`severity: "unknown"` means the source cannot show it. A share has no artifact rows, so `regex_v1` reports D1 as unknown there instead of inventing a number.

## Sources

Built in, behind `--loader auto`: a SharedNet share link or token, a saved share JSON, a `sharednet room export` NDJSON, and a bench episode directory (`room.ndjson`, `ops.jsonl`, `episode.json`). A share shows posts and seats; an export adds artifact rows; an episode adds per-seat ops. The more the source shows, the more the annotator can verify.

Anything else is a loader: any function from a source string to a `Trace`, registered as an entry point (below). Or build the `Trace` yourself:

```python
from commsfail import Trace

trace = Trace(
    room={"name": "run-17"},
    seats=[{"handle": "planner"}, {"handle": "coder"}],
    posts=[{"seq": 1, "who": "planner", "text": "I'll take the parser.", "created_at": "2026-10-06T10:00:00Z",
            "reply_to": None, "type": "message"}],
    source={"kind": "rollout", "path": "run-17.jsonl"},
)
```

## Plugins

Annotators and loaders live in your own package and announce themselves through entry points:

```toml
[project.entry-points."commsfail.annotators"]
my_v1 = "my_package.annotators:MyV1"

[project.entry-points."commsfail.loaders"]
chat_jsonl = "my_package.loaders:load_chat_jsonl"
```

An annotator is a class with `name`, `version` and `annotate(trace) -> dict`. Start from `base_analysis`, which returns a conforming record with every mode absent:

```python
from commsfail import base_analysis, set_mode

class MyV1:
    """One line on what it is good at. This line shows in `commsfail annotators`."""
    name = "my_v1"
    version = "0.1.0"

    def annotate(self, trace):
        a = base_analysis(trace, self)
        ...  # fill a["metrics"] and a["items"], then for each mode you have evidence for:
        set_mode(a, "D2", evidence=[{"seq": 17, "who": "B", "excerpt": "LGTM on utils.py", "why": "utils.py was never delivered"}],
                 severity="low", confidence=0.6)
        return a
```

[`examples/plugin/`](examples/plugin) is a complete, installable plugin with one annotator and one loader. Copy it. Once it is installed, `commsfail annotators` lists it, `--annotator my_v1` runs it, and the contract tests in this repository run on it too.

The contract, enforced by `tests/test_contract.py` on every registered annotator:

- every mode id is present in `modes`, even when absent, so records from different annotators line up column for column;
- `confidence` is per mode, and `severity` is `"unknown"` when the source cannot show the mode;
- evidence rows are `{seq, who, excerpt, why}`, the excerpt redacted, at most 25 per mode, every `seq` a post that exists;
- `annotate()` is deterministic and makes no network call, so a record can be recomputed offline from the saved trace;
- a model-as-judge annotator records the model and the prompt hash in `source`, and never sees an outcome grade or an experimental condition.

## What it is not

It does not grade the task. Whether the team solved the problem is a separate measurement, kept out of the annotator's sight so that a record describes the conversation and nothing else. And it does not label: `regex_v1` is a set of calibrated patterns that point a reader at the right posts. The `annotation` block is where human labels go.

## Status

0.1.0. The taxonomy and the record follow a paper under anonymous review; the citation will be added when it is public. `regex_v1` was calibrated on SharedNet Rooms. A model-as-judge annotator and a human-label importer are planned as plugins. Contributions: [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT.
