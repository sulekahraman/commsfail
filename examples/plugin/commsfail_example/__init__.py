"""A minimal commsfail plugin: one annotator and one loader for a transcript format commsfail does not know.

Install it next to commsfail and both show up in the CLI through the entry points declared in pyproject.toml.
Copy this directory to start your own.
"""
from __future__ import annotations
import json
from pathlib import Path
from commsfail import Trace, base_analysis, set_mode

class ExampleV1:
    """Flags D3 when the board ends on an open question. A placeholder for your method, not a method."""
    name = "example_v1"
    version = "0.1.0"

    def annotate(self, trace: Trace) -> dict:
        a = base_analysis(trace, self)
        last = trace.posts[-1] if trace.posts else None
        if last and last["text"].rstrip().endswith("?"):
            set_mode(a, "D3", evidence=[{"seq": last["seq"], "who": last["who"], "excerpt": last["text"][:160],
                                         "why": "the board ends on a question nobody answered"}],
                     severity="low", confidence=0.4)
            a["metrics"]["last_post_kind"] = "ask"
        a["caveats"].append("example annotator: it only looks at the last post")
        return a

def load_chat_jsonl(path: str) -> Trace:
    """One JSON object per line: {"turn": 3, "speaker": "planner", "text": "...", "t": "2026-...", "model": "..."}."""
    p = Path(path)
    posts, seats = [], {}
    for i, line in enumerate(p.read_text(encoding="utf-8").splitlines()):
        if not line.strip():
            continue
        row = json.loads(line)
        who = row.get("speaker") or "?"
        seats.setdefault(who, {"handle": who, "label": None, "driver": row.get("model"), "joined_at": None, "principal": None})
        posts.append({"seq": int(row.get("turn", i + 1)), "who": who, "text": row.get("text") or "",
                      "created_at": row.get("t"), "reply_to": None, "type": "message"})
    posts.sort(key=lambda x: x["seq"])
    return Trace(room={"name": p.stem, "created_at": posts[0]["created_at"] if posts else None,
                       "latest_sequence": posts[-1]["seq"] if posts else 0},
                 seats=list(seats.values()), posts=posts, source={"kind": "chat-jsonl", "path": str(p)})
