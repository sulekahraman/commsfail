"""Behaviour of message_annotations_v1: bounded prompts and normalized cached labels."""
import json

from commsfail.annotators.message_annotations_v1 import (
    CACHE_FORMAT,
    MessageAnnotationsV1,
    annotation_context,
    build_requests,
    trace_fingerprint,
)
from commsfail.trace import Trace


def _trace() -> Trace:
    return Trace(
        room={"name": "annotation-test"},
        seats=[
            {"handle": "builder", "label": "Builder", "driver": "codex"},
            {"handle": "reviewer", "label": "Reviewer", "driver": "claude-code"},
        ],
        posts=[
            {
                "seq": 1,
                "who": "builder",
                "text": "I will prepare the parser.",
                "created_at": "2026-10-07T10:00:00Z",
                "reply_to": None,
                "type": "message",
                "role": "agent",
            },
            {
                "seq": 2,
                "who": "reviewer",
                "text": "Please send the result when it is ready.",
                "created_at": "2026-10-07T10:01:00Z",
                "reply_to": 1,
                "type": "message",
                "role": "agent",
            },
            {
                "seq": 3,
                "who": "builder",
                "text": "Reviewer, the result is ready in file_parserA. See #2.",
                "created_at": "2026-10-07T10:02:00Z",
                "reply_to": None,
                "type": "message",
                "role": "agent",
            },
        ],
        source={"kind": "share-file"},
    )


def _cache(trace: Trace) -> dict:
    return {
        "format": CACHE_FORMAT,
        "guide_version": "1.0",
        "trace_fingerprint": trace_fingerprint(trace),
        "annotations": [
            {
                "seq": 3,
                "primary_type": "result_delivery",
                "secondary_types": [
                    "result_delivery",
                    "artifact_sharing",
                    "coordination",
                ],
                "replies_to": [2, 3, 99, 2],
                "addressed_to": ["reviewer", "unknown", "reviewer"],
                "confidence": 0.9,
                "ambiguous": False,
                "rationale": "Delivers the requested result.",
                "evidence": [
                    {"field": "primary_type", "text": "the result is ready"},
                    {"field": "addressed_to", "text": "not in the target"},
                ],
            }
        ],
    }


def test_requests_use_only_bounded_prior_context():
    trace = _trace()
    requests = build_requests(trace)
    third = requests[2]
    assert third["seq"] == 3
    assert "#2 reviewer" in third["prompt"]
    assert "Every number in replies_to must be lower than 3" in third["prompt"]
    context = annotation_context(trace, trace.posts[2])
    assert [row["seq"] for row in context["cited_messages"]] == [2]
    assert context["hints"] == {
        "cites": [2],
        "addressed_to": ["reviewer"],
        "artifacts": ["file_parserA"],
        "heartbeat": False,
    }


def test_cached_labels_are_normalized_and_coverage_is_explicit():
    trace = _trace()
    output = MessageAnnotationsV1(_cache(trace)).annotate(trace)
    assert output["status"] == "partial"
    assert output["coverage"] == {
        "agent_posts": 3,
        "annotated": 1,
        "missing": [1, 2],
    }
    assert output["messages"] == [
        {
            "seq": 3,
            "who": "builder",
            "primary_type": "result_delivery",
            "secondary_types": ["artifact_sharing", "coordination"],
            "replies_to": [2],
            "addressed_to": ["reviewer"],
            "confidence": 0.9,
            "ambiguous": False,
            "rationale": "Delivers the requested result.",
            "evidence": [
                {"field": "primary_type", "text": "the result is ready"}
            ],
        }
    ]


def test_a_stale_cache_is_not_applied():
    trace = _trace()
    cache = _cache(trace)
    cache["trace_fingerprint"] = "0" * 64
    output = MessageAnnotationsV1(cache).annotate(trace)
    assert output["status"] == "invalid_cache"
    assert output["messages"] == []
    assert "different trace revision" in output["caveats"][0]


def test_a_malformed_sidecar_is_invalid_not_missing(tmp_path):
    trace = _trace()
    sidecar = tmp_path / "bad.json"
    sidecar.write_text("{bad", encoding="utf-8")
    output = MessageAnnotationsV1(sidecar).annotate(trace)
    assert output["status"] == "invalid_cache"
    assert "not valid JSON" in output["caveats"][0]

    sidecar.write_text(json.dumps([]), encoding="utf-8")
    output = MessageAnnotationsV1(sidecar).annotate(trace)
    assert output["status"] == "invalid_cache"
    assert "JSON object" in output["caveats"][0]
