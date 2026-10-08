"""Structured per-message discourse annotations from an offline model cache.

The model-facing step is separate: ``build_requests`` writes bounded prompts,
and ``write_cache`` stores the resulting structured answers. ``annotate`` only
reads that cache, validates it against the trace, and returns normalized rows.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from commsfail.sources.sharednet import agent_posts, cites, mentions, redact
from commsfail.trace import Trace

MESSAGE_TYPES = (
    "question",
    "delegation_request",
    "acknowledgement",
    "status_update",
    "result_delivery",
    "evidence_observation",
    "proposal",
    "critique_disagreement",
    "agreement",
    "decision",
    "synthesis",
    "clarification",
    "artifact_sharing",
    "coordination",
    "social_heartbeat",
)
GUIDE_VERSION = "1.0"
REQUEST_FORMAT = "commsfail/message_annotations_v1/request.v1"
CACHE_FORMAT = "commsfail/message_annotations_v1/cache.v1"
CACHE_NAME = "message_annotations_v1.json"

TYPE_GUIDE = """
- question: asks for information, evaluation, clarification, or a decision
- delegation_request: assigns or requests concrete work from another agent
- acknowledgement: confirms receipt or understanding without substantive work
- status_update: reports progress, blockage, or current activity
- result_delivery: delivers completed analysis, output, or requested work
- evidence_observation: contributes facts, measurements, or observations
- proposal: suggests a plan, hypothesis, design, or next action
- critique_disagreement: challenges, rejects, or identifies a problem
- agreement: explicitly accepts or endorses another contribution
- decision: commits the group to a choice or conclusion
- synthesis: combines multiple contributions into a unified account
- clarification: resolves ambiguity or corrects interpretation
- artifact_sharing: publishes or points to a file, link, run, or other artifact
- coordination: manages sequencing, ownership, deadlines, or process
- social_heartbeat: greeting, availability ping, or low-content presence update
""".strip()

RULES = """
1. Label only the target message.
2. Describe observable communicative function, not quality or success.
3. Choose one primary type and at most two secondary types.
4. Keep explicit citations separate from inferred replies_to relationships.
5. Every replies_to number must be earlier than the target message number.
6. Support inferred fields with short target-message evidence; mark real uncertainty.
""".strip()

ARTIFACT_RE = re.compile(r"\b(?:art|shr|run|tool|file)_[A-Za-z0-9_-]+\b")
HEARTBEAT_RE = re.compile(
    r"^\s*(?:heartbeat|ping|still working|working on it|status update|no update)\b",
    re.I,
)


def trace_fingerprint(trace: Trace) -> str:
    """A stable digest of the roster and ordered posts used by this annotator."""
    payload = {
        "seats": [
            {
                "handle": seat.get("handle"),
                "label": seat.get("label"),
                "driver": seat.get("driver"),
                "model": seat.get("model"),
            }
            for seat in trace.seats
        ],
        "posts": [
            {
                "seq": post.get("seq"),
                "who": post.get("who"),
                "text": post.get("text"),
                "created_at": post.get("created_at"),
                "reply_to": post.get("reply_to"),
                "role": post.get("role"),
            }
            for post in trace.posts
        ],
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def cache_path(trace: Trace) -> Path | None:
    """The conventional sidecar path for a local source, or None for a URL."""
    source = trace.source.get("path")
    if not source:
        return None
    path = Path(source)
    if path.is_dir():
        return path / CACHE_NAME
    return path.with_name(path.name + "." + CACHE_NAME)


def _summary(post: dict, limit: int) -> dict:
    return {
        "seq": post.get("seq"),
        "who": post.get("who"),
        "created_at": post.get("created_at"),
        "text": str(post.get("text") or "")[:limit],
    }


def _addressed_to(text: str, trace: Trace, author: str) -> list[str]:
    roster = {seat.get("handle") for seat in trace.seats if seat.get("handle")}
    addressed = [handle for handle in mentions(text) if handle in roster and handle != author]
    lower = text.lower()
    for seat in trace.seats:
        handle, label = seat.get("handle"), seat.get("label")
        if not handle or handle == author or handle in addressed:
            continue
        if label and len(label) >= 3 and label.lower() in lower:
            addressed.append(handle)
    return addressed


def annotation_context(trace: Trace, target: dict) -> dict:
    """Bounded prior context and deterministic hints for one target post."""
    seq = target["seq"]
    by_seq = {post["seq"]: post for post in trace.posts}
    cited = []
    for number in [target.get("reply_to"), *cites(target.get("text") or "")]:
        if isinstance(number, int) and number < seq and number in by_seq and number not in cited:
            cited.append(number)
    prior = [post for post in trace.posts if post["seq"] < seq]
    text = target.get("text") or ""
    return {
        "roster": [
            {
                "handle": seat.get("handle"),
                "label": seat.get("label"),
                "driver": seat.get("driver"),
                "model": seat.get("model"),
            }
            for seat in trace.seats
        ],
        "cited_messages": [_summary(by_seq[number], 2_000) for number in cited[:6]],
        "previous_messages": [_summary(post, 500) for post in prior[-12:]],
        "hints": {
            "cites": cited[:6],
            "addressed_to": _addressed_to(text, trace, target.get("who")),
            "artifacts": list(dict.fromkeys(ARTIFACT_RE.findall(text))),
            "heartbeat": bool(HEARTBEAT_RE.search(text)),
        },
    }


def build_prompt(trace: Trace, target: dict) -> str:
    """The complete bounded prompt for one target post."""
    context = annotation_context(trace, target)

    def messages(rows: list[dict]) -> str:
        if not rows:
            return "None."
        return "\n\n".join(
            f"#{row['seq']} {row.get('who') or 'unknown'} "
            f"({row.get('created_at') or 'unknown-time'}):\n{row.get('text') or ''}"
            for row in rows
        )

    roster = "\n".join(
        f"- {seat.get('handle')}: {seat.get('label') or 'unlabeled'}, "
        f"{seat.get('driver') or 'unknown driver'}"
        for seat in context["roster"]
    ) or "- unavailable"
    return f"""
You are annotating one message from a multi-agent collaboration trace.
Agents work asynchronously in one shared, ordered room.

MESSAGE TYPES:
{TYPE_GUIDE}

RULES:
{RULES}

AGENT ROSTER:
{roster}

MESSAGES THE TARGET EXPLICITLY CITES:
{messages(context["cited_messages"])}

THE 12 MESSAGES IMMEDIATELY BEFORE THE TARGET:
{messages(context["previous_messages"])}

RULE-BASED HINTS FOR THE TARGET:
{json.dumps(context["hints"], sort_keys=True)}

TARGET MESSAGE TO LABEL:
#{target["seq"]} {target.get("who") or "unknown"} ({target.get("created_at") or "unknown-time"}):
{str(target.get("text") or "")[:8_000]}

Return JSON with primary_type, secondary_types, replies_to, addressed_to,
confidence, ambiguous, rationale, and evidence. Label only the target message.
Every number in replies_to must be lower than {target["seq"]}. addressed_to
must use roster handles. Evidence spans must come from the target message.
""".strip()


def build_requests(trace: Trace) -> list[dict]:
    """One model request per agent post, with no future-message context."""
    fingerprint = trace_fingerprint(trace)
    return [
        {
            "format": REQUEST_FORMAT,
            "guide_version": GUIDE_VERSION,
            "trace_fingerprint": fingerprint,
            "seq": post["seq"],
            "prompt": build_prompt(trace, post),
        }
        for post in agent_posts(trace)
    ]


def write_requests(trace: Trace, path: str | Path) -> None:
    """Write model requests as JSONL for a separate model-running step."""
    rows = build_requests(trace)
    Path(path).write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def write_cache(trace: Trace, annotations: list[dict], path: str | Path | None = None) -> Path:
    """Write raw structured model answers in the versioned sidecar envelope."""
    destination = Path(path) if path is not None else cache_path(trace)
    if destination is None:
        raise ValueError("A cache path is required for a source without a local path.")
    payload = {
        "format": CACHE_FORMAT,
        "guide_version": GUIDE_VERSION,
        "trace_fingerprint": trace_fingerprint(trace),
        "annotations": annotations,
    }
    destination.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return destination


def _load_cache(
    trace: Trace,
    supplied: dict | str | Path | None,
) -> tuple[dict | None, str | None, str | None]:
    if isinstance(supplied, dict):
        return supplied, None, None
    path = Path(supplied) if supplied is not None else cache_path(trace)
    if path is None or not path.is_file():
        return None, "No annotation cache was found for this source.", "missing_cache"
    try:
        cache = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        return None, f"The annotation cache is not valid JSON: {error.msg}.", "invalid_cache"
    if not isinstance(cache, dict):
        return None, "The annotation cache must be a JSON object.", "invalid_cache"
    return cache, None, None


def _normalize(raw: dict, target: dict, real_seqs: set[int], roster: set[str]) -> dict | None:
    primary = raw.get("primary_type")
    confidence = raw.get("confidence")
    ambiguous = raw.get("ambiguous")
    if (
        primary not in MESSAGE_TYPES
        or not isinstance(confidence, (int, float))
        or not isinstance(ambiguous, bool)
    ):
        return None
    if isinstance(confidence, bool) or not 0 <= confidence <= 1:
        return None

    secondary = []
    for label in raw.get("secondary_types") or []:
        if label in MESSAGE_TYPES and label != primary and label not in secondary:
            secondary.append(label)
    replies = sorted({
        number
        for number in raw.get("replies_to") or []
        if isinstance(number, int)
        and not isinstance(number, bool)
        and number in real_seqs
        and 0 < number < target["seq"]
    })
    addressed = list(dict.fromkeys(
        handle for handle in raw.get("addressed_to") or [] if handle in roster
    ))
    text = target.get("text") or ""
    evidence = []
    for item in raw.get("evidence") or []:
        if not isinstance(item, dict):
            continue
        span = item.get("text")
        field = item.get("field")
        if isinstance(field, str) and isinstance(span, str) and span and span in text:
            evidence.append({"field": field[:80], "text": redact(span)})

    return {
        "seq": target["seq"],
        "who": target.get("who") or "",
        "primary_type": primary,
        "secondary_types": secondary[:2],
        "replies_to": replies,
        "addressed_to": addressed,
        "confidence": float(confidence),
        "ambiguous": ambiguous,
        "rationale": redact(str(raw.get("rationale") or ""), 500),
        "evidence": evidence[:3],
    }


class MessageAnnotationsV1:
    """Normalize cached model labels for the 15-type message-function guide."""

    name = "message_annotations_v1"
    version = "0.1.0"
    schema = "schema.json"

    def __init__(self, cache: dict | str | Path | None = None):
        self.cache = cache

    def annotate(self, trace: Trace) -> dict:
        posts = agent_posts(trace)
        fingerprint = trace_fingerprint(trace)
        cache, error, load_status = _load_cache(trace, self.cache)
        caveats = [error] if error else []
        status = load_status or "complete"

        if cache is not None and cache.get("format") != CACHE_FORMAT:
            caveats.append(f"Expected cache format {CACHE_FORMAT}.")
            cache, status = None, "invalid_cache"
        if cache is not None and cache.get("trace_fingerprint") != fingerprint:
            caveats.append("The annotation cache belongs to a different trace revision.")
            cache, status = None, "invalid_cache"
        if cache is not None and not isinstance(cache.get("annotations"), list):
            caveats.append("The annotation cache must contain an annotations array.")
            cache, status = None, "invalid_cache"

        raw_by_seq = {}
        if cache is not None:
            for item in cache.get("annotations") or []:
                if (
                    isinstance(item, dict)
                    and isinstance(item.get("seq"), int)
                    and not isinstance(item.get("seq"), bool)
                ):
                    raw_by_seq.setdefault(item["seq"], item)

        real_seqs = {post["seq"] for post in trace.posts}
        roster = {seat.get("handle") for seat in trace.seats if seat.get("handle")}
        annotations = []
        invalid = []
        for post in posts:
            raw = raw_by_seq.get(post["seq"])
            if raw is None:
                continue
            normalized = _normalize(raw, post, real_seqs, roster)
            if normalized is None:
                invalid.append(post["seq"])
            else:
                annotations.append(normalized)

        missing = sorted({post["seq"] for post in posts} - {row["seq"] for row in annotations})
        if cache is not None and missing:
            status = "partial"
        if invalid:
            caveats.append(f"Invalid cached annotations were ignored for posts {invalid}.")
        if missing:
            caveats.append(f"No valid annotation is available for {len(missing)} agent post(s).")

        return {
            "guide_version": GUIDE_VERSION,
            "cache_format": CACHE_FORMAT,
            "trace_fingerprint": fingerprint,
            "status": status,
            "messages": annotations,
            "coverage": {
                "agent_posts": len(posts),
                "annotated": len(annotations),
                "missing": missing,
            },
            "caveats": caveats,
        }

    def markdown(self, output: dict) -> str:
        coverage = output["coverage"]
        lines = [
            f"{coverage['annotated']}/{coverage['agent_posts']} agent posts annotated "
            f"({output['status']}).",
            "",
        ]
        lines += [
            f"- #{row['seq']} {row['who']}: {row['primary_type']} "
            f"({row['confidence']:.2f})"
            for row in output["messages"]
        ]
        lines += [f"- Caveat: {item}" for item in output["caveats"]]
        return "\n".join(lines)


ANNOTATOR = MessageAnnotationsV1
