"""Loaders produce the same Trace shape from a share JSON and from a room export NDJSON."""
import json
from commsfail.trace import load_trace

def test_share_json_loader(tmp_path):
    share = {"room": {"name": "r", "created_at": "2026-09-20T10:00:00Z", "latest_sequence": 2},
             "members": [{"handle": "A", "label": "Engineer", "driver": "claude-code", "joined_at": "2026-09-20T10:00:00Z", "kind": "account", "status": "active"}],
             "messages": [{"sequence": 1, "content": "hi", "created_at": "2026-09-20T10:01:00Z", "reply_to_sequence": None, "sender": {"handle": "A", "label": "Engineer", "driver": "claude-code", "kind": "account"}},
                          {"sequence": 2, "content": "re", "created_at": "2026-09-20T10:02:00Z", "reply_to_sequence": 1, "sender": {"handle": "A", "label": "Engineer", "driver": "claude-code", "kind": "account"}}]}
    p = tmp_path / "share.json"; p.write_text(json.dumps(share), encoding="utf-8")
    t = load_trace(str(p))
    assert t.source["kind"] == "share-file" and not t.has_record
    assert [x["seq"] for x in t.posts] == [1, 2] and t.posts[1]["reply_to"] == 1
    assert t.seats[0]["handle"] == "A" and t.artifacts == []

def test_export_ndjson_loader(tmp_path):
    rows = [{"kind": "room", "id": "rom_x", "name": "r", "created_at": "2026-09-20T10:00:00Z"},
            {"kind": "member", "instance_id": "i_A", "principal_id": "p_1", "runtime_kind": "codex", "joined_at": "2026-09-20T10:00:00Z", "display_name": "A"},
            {"kind": "message", "sequence": 2, "sender_instance_id": "i_A", "content": "second", "created_at": "2026-09-20T10:02:00Z", "type": "message"},
            {"kind": "message", "sequence": 1, "sender_instance_id": "i_A", "content": "first", "created_at": "2026-09-20T10:01:00Z", "type": "message"},
            {"kind": "artifact", "id": "art_1", "uploaded_by_instance_id": "i_A", "created_at": "2026-09-20T10:03:00Z", "filename": "a.txt", "sha256": "00"},
            {"kind": "end", "latest_sequence": 2}]
    p = tmp_path / "room.ndjson"; p.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    t = load_trace(str(p))
    assert t.source["kind"] == "export" and t.has_record
    assert [x["seq"] for x in t.posts] == [1, 2]               # sorted
    assert t.seats[0]["principal"] == "p_1" and t.artifacts[0]["by"] == "i_A"
