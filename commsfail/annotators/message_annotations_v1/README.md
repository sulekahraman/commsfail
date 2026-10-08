# message_annotations_v1

Structured labels for what each agent post is doing in the conversation. This
annotator reports discourse function, not whether the post or collaboration was
successful.

Each post receives one primary type and at most two secondary types:
`question`, `delegation_request`, `acknowledgement`, `status_update`,
`result_delivery`, `evidence_observation`, `proposal`,
`critique_disagreement`, `agreement`, `decision`, `synthesis`,
`clarification`, `artifact_sharing`, `coordination`, or `social_heartbeat`.
Rows also contain earlier reply links, addressed seats, confidence, ambiguity,
a rationale, and up to three target-post evidence spans.

## How

Model calls happen before `annotate()`. The preparation step gives each target
only the roster, up to six cited earlier posts, the twelve preceding posts,
deterministic hints, and the target itself. It never includes future posts.
One request labels one target, but the target is therefore not classified
without context. This per-target design makes retries, caching, and historical
reply constraints simple. Its cost grows with the number of posts because the
guide and overlapping context are repeated; a future runner may batch targets
while preserving a separate bounded context for each one.

Message classification is optional. A missing cache is a valid result with
`status: "missing_cache"` rather than an error. This supports an ablation in
which the same conversation-level scanner is evaluated first on the raw trace
and then with message annotations, holding its model, prompt, token budget, and
evaluation set fixed. The comparison should report accuracy, citation quality,
latency, and token cost before annotations become a required preprocessing
step.

Export one JSONL request per agent post:

```python
from commsfail import load
from commsfail.annotators.message_annotations_v1 import write_requests

trace = load("runs/rom_abc")
write_requests(trace, "message-annotation-requests.jsonl")
```

Run those prompts with a structured-output model. Each answer has:

```json
{
  "seq": 7,
  "primary_type": "result_delivery",
  "secondary_types": ["artifact_sharing"],
  "replies_to": [4],
  "addressed_to": ["reviewer"],
  "confidence": 0.92,
  "ambiguous": false,
  "rationale": "Delivers the requested result and names its artifact.",
  "evidence": [{"field": "primary_type", "text": "The result is ready"}]
}
```

Write the answers to the conventional sidecar:

```python
from commsfail.annotators.message_annotations_v1 import write_cache

write_cache(trace, answers)
```

For a record folder the sidecar is `message_annotations_v1.json` inside the
folder. For a local file it is `<source>.message_annotations_v1.json`. A share
URL should first be saved as a local share JSON. `commsfail analyse` then reads
the sidecar offline:

```bash
commsfail analyse runs/rom_abc --annotator message_annotations_v1 --markdown
```

The cache includes a trace fingerprint. Stale or malformed caches are not
silently applied. Missing and invalid labels appear in `coverage` and
`caveats`; model-provided text is redacted before it reaches the record.

**Good at:** producing reusable, bounded, message-level features for later
failure analysis; separating observable message function from conversation
outcomes; making uncertainty and coverage explicit.

**Weak at:** labels are model judgments and inherit the model and prompt's
errors. The categories may overlap, inferred reply links can be uncertain, and
the bounded context can omit older implicit dependencies. Validate on
human-labeled data and record the model, prompt, and generation settings with
the cache in the study that produced it.

**Checked on:** the repository's synthetic trace, including historical
citations, roster filtering, evidence spans, stale caches, and missing labels.
