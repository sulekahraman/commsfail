"""The analysis.v1 contract. An annotator's output must pass ``validate()``; the tests enforce it.

Top level: schema, source, room, metrics, items, modes, annotation, caveats.
``modes`` has exactly one entry per id in MODES (the paper's eight plus REP and HB), each with
present, severity, count, confidence, removed_by, evidence[{seq, who, excerpt, why}].
"""
from __future__ import annotations

SCHEMA = "comms-failure/analysis.v1"

# id -> (name, group, layer that removes it). Groups and layers are the paper's Table 2.
MODES = {
    "R1":  ("Open-set decay",            "not_read",    "view"),
    "R2":  ("Replacement re-does work",  "not_read",    "view"),
    "B1":  ("Belief without commitment", "not_binding", "naming"),
    "B2":  ("Identity drift",            "not_binding", "check"),
    "D1":  ("Unattested action",         "never_done",  "check"),
    "D2":  ("Review of nothing",         "never_done",  "check"),
    "D3":  ("Closure before budget",     "never_done",  "none"),
    "D4":  ("Capability not routed",     "never_done",  "none"),
    "REP": ("Step repetition",           "not_read",    "view"),
    "HB":  ("Heartbeat cost",            "never_done",  "none"),
}
SEVERITIES = ("none", "low", "medium", "high", "unknown")
LAYERS = ("naming", "view", "check", "none")
TOP_KEYS = ("schema", "source", "room", "metrics", "items", "modes", "annotation", "caveats")
METRIC_KEYS = ("posts", "seats", "asks", "asks_unanswered", "claims", "re_claims", "heartbeat_posts", "heartbeat_share", "open_items_at_end", "last_post_kind")
EVIDENCE_KEYS = ("seq", "who", "excerpt", "why")

FIELD_DOC = {
    "schema": SCHEMA,
    "source": "kind share|share-file|export|episode, token redacted or path, fetched_at",
    "room": "name, created_at, latest_sequence, seats [{handle, label, driver, joined_at, principal}]",
    "metrics": "room-level counts the modes are rates of: " + ", ".join(METRIC_KEYS) + ", and more",
    "items": "work items extracted from text: per item the claim/done/review/upload trajectory and status_at_end",
    "modes": "one entry per mode id: present, severity, count, confidence 0-1, removed_by, evidence [{seq, who, excerpt, why}]",
    "annotation": "Table 1 slots for humans: labels accept/result/review_pass, facts delivered/acted/passed, uncertain, annotators, adjudicated",
    "caveats": "what this source cannot show",
}

def empty_annotation() -> dict:
    return {"labels": {"accept": {}, "result": {}, "review_pass": {}},
            "facts": {"delivered": {}, "acted": {}, "passed": {}},
            "uncertain": [], "annotators": [], "adjudicated": False}

def validate(a: dict) -> list[str]:
    """Return a list of problems; empty means the analysis conforms."""
    errs = []
    if not isinstance(a, dict): return ["analysis is not an object"]
    for k in TOP_KEYS:
        if k not in a: errs.append(f"missing top-level key '{k}'")
    if a.get("schema") != SCHEMA: errs.append(f"schema must be '{SCHEMA}'")
    m = a.get("metrics") or {}
    for k in METRIC_KEYS:
        if k not in m: errs.append(f"metrics missing '{k}'")
    modes = a.get("modes") or []
    ids = [x.get("id") for x in modes]
    for mid in MODES:
        if mid not in ids: errs.append(f"modes missing '{mid}'")
    for x in modes:
        mid = x.get("id")
        if mid not in MODES: errs.append(f"unknown mode id '{mid}'"); continue
        if x.get("severity") not in SEVERITIES: errs.append(f"{mid}: severity must be one of {SEVERITIES}")
        if x.get("removed_by") not in LAYERS: errs.append(f"{mid}: removed_by must be one of {LAYERS}")
        c = x.get("confidence")
        if not isinstance(c, (int, float)) or not 0 <= c <= 1: errs.append(f"{mid}: confidence must be a number in [0,1]")
        if not isinstance(x.get("count"), int): errs.append(f"{mid}: count must be an int")
        if not isinstance(x.get("present"), bool): errs.append(f"{mid}: present must be a bool")
        for e in x.get("evidence") or []:
            for k in EVIDENCE_KEYS:
                if k not in e: errs.append(f"{mid}: evidence row missing '{k}'")
    ann = a.get("annotation") or {}
    for k in ("labels", "facts", "uncertain", "annotators", "adjudicated"):
        if k not in ann: errs.append(f"annotation missing '{k}'")
    return errs
