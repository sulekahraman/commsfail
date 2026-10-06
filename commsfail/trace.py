"""A Trace is one Room in a normalized shape. Every loader produces the same thing, so an annotator never
cares whether the Room came from a share link, a server export, or a bench episode directory.

    Trace
      .room      {name, created_at, latest_sequence, ...}
      .seats     [{handle, label, driver, joined_at, principal}]
      .posts     [{seq, who, text, created_at, reply_to, type}]        who = seat handle; type = "message" | server kinds
      .artifacts [{id, by, created_at, name, sha256}]                   empty on a share
      .ops       {handle: [{at, kind, argv|path|tool, exit_code, hash}]}  per-seat execution trace; empty unless an episode dir
      .source    {kind, path|token, fetched_at}
"""
from __future__ import annotations
import json, os, urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

SHARE_API = "https://www.sharednet.ai/api/sharednet/shared/{token}"

@dataclass
class Trace:
    room: dict
    seats: list
    posts: list
    artifacts: list = field(default_factory=list)
    ops: dict = field(default_factory=dict)
    source: dict = field(default_factory=dict)

    @property
    def has_record(self) -> bool:
        """True when artifact rows (and possibly per-seat ops) exist, so 'delivered' and 'acted' facts can be read by rule."""
        return self.source.get("kind") in ("export", "episode")

def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def parse_ts(s):
    if not s: return None
    try: return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except Exception: return None

def _from_share(d: dict, source: dict) -> Trace:
    seats = [{"handle": m.get("handle"), "label": m.get("label"), "driver": m.get("driver"),
              "joined_at": m.get("joined_at"), "principal": m.get("principal")} for m in d.get("members", [])]
    posts = [{"seq": m["sequence"], "who": (m.get("sender") or {}).get("handle") or "?", "text": m.get("content") or "",
              "created_at": m.get("created_at"), "reply_to": m.get("reply_to_sequence"), "type": m.get("type") or "message"}
             for m in sorted(d.get("messages", []), key=lambda m: m["sequence"])]
    return Trace(room=d.get("room", {}), seats=seats, posts=posts, artifacts=[], source=source)

def _from_export(lines: list[str], source: dict) -> Trace:
    room, seats, posts, arts = {}, [], [], []
    for line in lines:
        if not line.strip(): continue
        row = json.loads(line); k = row.get("kind")
        if k == "room": room = row
        elif k == "member":
            seats.append({"handle": row.get("instance_id"), "label": row.get("display_name"), "driver": row.get("runtime_kind"),
                          "joined_at": row.get("joined_at"), "principal": row.get("principal_id")})
        elif k == "message":
            posts.append({"seq": row["sequence"], "who": row.get("sender_instance_id") or "?", "text": row.get("content") or "",
                          "created_at": row.get("created_at"), "reply_to": None, "type": row.get("type") or "message"})
        elif k == "artifact":
            arts.append({"id": row.get("id"), "by": row.get("uploaded_by_instance_id"), "created_at": row.get("created_at"),
                         "name": row.get("filename"), "sha256": row.get("sha256")})
    return Trace(room=room, seats=seats, posts=sorted(posts, key=lambda p: p["seq"]), artifacts=arts, source=source)

def _from_episode_dir(p: Path) -> Trace:
    """A bench episode directory (data/RECORD.md): room.ndjson + ops.jsonl (+ episode.json)."""
    t = _from_export((p / "room.ndjson").read_text(encoding="utf-8").splitlines(), {"kind": "episode", "path": str(p), "fetched_at": _now()})
    ops = {}
    if (p / "ops.jsonl").exists():
        for line in (p / "ops.jsonl").read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line); ops.setdefault(row.get("seat"), []).append(row)
    t.ops = ops
    if (p / "episode.json").exists():
        t.room = {**json.loads((p / "episode.json").read_text(encoding="utf-8")), **t.room}
    return t

def load_trace(src: str) -> Trace:
    """Accepts a share link, a shr_ token, a saved share JSON, a room export NDJSON, or an episode directory."""
    if src.startswith("http") or src.startswith("shr_"):
        token = src.rsplit("/", 1)[-1]
        with urllib.request.urlopen(SHARE_API.format(token=token), timeout=30) as r:
            return _from_share(json.load(r), {"kind": "share", "token": token[:8] + "…", "fetched_at": _now()})
    p = Path(src)
    if p.is_dir():
        return _from_episode_dir(p)
    text = p.read_text(encoding="utf-8")
    if text.lstrip().startswith("{") and '"messages"' in text[:4000]:
        return _from_share(json.loads(text), {"kind": "share-file", "path": str(p), "fetched_at": _now()})
    return _from_export(text.splitlines(), {"kind": "export", "path": str(p), "fetched_at": _now()})
