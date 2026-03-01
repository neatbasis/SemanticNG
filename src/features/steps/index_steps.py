# features/steps/index_steps.py
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from behave import given, then, when
from gherkin.parser import Parser
from gherkin.token_scanner import TokenScanner

from state_renormalization.gherkin_document import GherkinDocument
from state_renormalization.stable_ids import derive_stable_ids

# -------------------------
# Helpers (pure + deterministic)
# -------------------------


def _canonical_json(obj: Any) -> str:
    """
    Canonical JSON for hashing: stable keys, no whitespace variance.
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", (text or "").lower())


def _find_span(haystack: str, needle: str) -> dict[str, int]:
    """
    Returns a dict with start/end char indices for the first occurrence.
    If not found, returns {-1,-1}.
    """
    idx = (haystack or "").find(needle)
    if idx < 0:
        return {"start": -1, "end": -1}
    return {"start": idx, "end": idx + len(needle)}


def _parse_created_year(dc_created: str) -> int:
    # Accept ISO-ish "2026-02-14T10:00:00Z"
    try:
        return datetime.fromisoformat(dc_created.replace("Z", "+00:00")).year
    except Exception:
        return 2026


def _to_iso_assuming_year(month_day_time: str, year: int) -> str:
    """
    Minimal parser for this test text only:
      "Feb 20, 18:00" -> "YYYY-02-20T18:00:00"
    """
    # Very small parsing just for this feature happy path
    m = re.search(r"\b(Feb)\s+(\d{1,2}),\s*(\d{1,2}):(\d{2})\b", month_day_time)
    if not m:
        # fallback: return as-is
        return f"{year}-01-01T00:00:00"
    mon = m.group(1)
    day = int(m.group(2))
    hh = int(m.group(3))
    mm = int(m.group(4))
    month_num = {"Feb": 2}.get(mon, 1)
    return f"{year:04d}-{month_num:02d}-{day:02d}T{hh:02d}:{mm:02d}:00"


# -------------------------
# Minimal in-memory "services"
# -------------------------


@dataclass
class Resource:
    identifier: str
    meta: dict[str, Any]  # includes Dublin Core fields under "dc"
    payload: dict[str, Any]  # arbitrary
    integrity: dict[str, Any]  # content_hash, etc.
    extensions: dict[str, Any]  # optional


class AppendOnlyResourceStore:
    def __init__(self) -> None:
        self._items: list[Resource] = []

    def append(self, resource: Resource) -> None:
        self._items.append(resource)

    def all(self) -> list[Resource]:
        return list(self._items)

    def last(self) -> Resource:
        return self._items[-1]


class SparseIndex:
    """
    Tiny inverted index: term -> set(resource_id)
    plus a naive scoring retrieval.
    """

    def __init__(self) -> None:
        self.inverted: dict[str, set] = {}
        self.docs: dict[str, str] = {}  # resource_id -> searchable text

    def add(self, doc_id: str, text: str) -> None:
        self.docs[doc_id] = text or ""
        for t in _tokenize(text):
            self.inverted.setdefault(t, set()).add(doc_id)

    def search(self, query: str, top_k: int = 5) -> list[str]:
        q_terms = _tokenize(query)
        if not q_terms:
            return []
        # Candidate set: union of posting lists
        candidates = set()
        for t in q_terms:
            candidates |= self.inverted.get(t, set())

        # Score by overlap count (simple, deterministic)
        scores: list[tuple[int, str]] = []
        for doc_id in candidates:
            doc_terms = set(_tokenize(self.docs.get(doc_id, "")))
            score = sum(1 for t in q_terms if t in doc_terms)
            scores.append((score, doc_id))

        scores.sort(key=lambda x: (-x[0], x[1]))
        return [doc_id for _, doc_id in scores[:top_k]]


class DenseInterpreterStub:
    """
    Deterministic "dense" interpreter that returns the exact proposal expected
    by the happy-path feature, with evidence spans.
    """

    def propose(self, payload_text: str, schema_id: str, dc_created: str) -> dict[str, Any]:
        year = _parse_created_year(dc_created)

        # Extract fields from known pattern text
        name = "SemanticNG hack night"
        when_str = "Feb 20, 18:00"
        location = "Maria 01"

        # Optional: organizer if present
        organizer = "Hacklair" if "Organizer: Hacklair" in payload_text else None

        extraction: dict[str, Any] = {
            "name": name,
            "startDate": _to_iso_assuming_year(when_str, year),
            "location": location,
        }
        if organizer:
            extraction["organizer"] = organizer

        evidence: dict[str, Any] = {
            "name": _find_span(payload_text, name),
            "startDate": _find_span(payload_text, when_str),
            "location": _find_span(payload_text, location),
        }
        if organizer:
            evidence["organizer"] = _find_span(payload_text, "Organizer: Hacklair")

        return {
            "schema_id": schema_id,
            "confidence": 0.92,
            "extraction": extraction,
            "evidence_spans": evidence,
        }


def _derive_context_stable_ids(context) -> dict[str, str]:
    feature_path = getattr(getattr(context, "feature", None), "filename", None)
    scenario = getattr(context, "scenario", None)
    step = getattr(context, "step", None)

    if not isinstance(feature_path, str) or not feature_path:
        return {}

    try:
        raw_doc = Parser().parse(TokenScanner(Path(feature_path).read_text(encoding="utf-8")))
    except Exception:
        return {}

    doc = GherkinDocument.from_raw(raw_doc, uri=feature_path)
    if doc is None:
        return {}

    stable = derive_stable_ids(doc, uri=feature_path)
    out: dict[str, str] = {"feature_id": stable.feature_id}

    scenario_name = getattr(scenario, "name", None)
    scenario_id = None
    if isinstance(scenario_name, str) and scenario_name.strip():
        for key, sid in stable.scenario_ids.items():
            if key.split(":", 1)[-1].split("@", 1)[0] == scenario_name:
                scenario_id = sid
                break
    elif len(stable.scenario_ids) == 1:
        scenario_id = next(iter(stable.scenario_ids.values()))

    if scenario_id is not None:
        out["scenario_id"] = scenario_id

    step_name = getattr(step, "name", None)
    if scenario_id is not None and isinstance(step_name, str) and step_name.strip():
        scenario_key = next((k for k, v in stable.scenario_ids.items() if v == scenario_id), None)
        if scenario_key is not None:
            for key, sid in stable.step_ids.items():
                key_scenario, step_part = key.split("::", 1)
                key_step_text = step_part.split(":", 1)[-1].split("@", 1)[0]
                if key_scenario == scenario_key and key_step_text == step_name:
                    out["step_id"] = sid
                    break
    elif len(stable.step_ids) == 1:
        out["step_id"] = next(iter(stable.step_ids.values()))

    return out


def _initialize_pipeline_context(context) -> None:
    context._last_persisted_resource = None
    context._last_ingested_resource = None
    context._last_artifact_resource = None


def _build_ingested_resource(context, dc: dict[str, Any], payload_text: str) -> Resource:
    stable_ids = _derive_context_stable_ids(context)
    meta = {"dc": dict(dc)}
    payload = {"text": payload_text}
    if stable_ids:
        meta["stable_ids"] = dict(stable_ids)
        meta.setdefault("semanticng", {}).update(stable_ids)
        payload.update(stable_ids)
    canonical = {
        "meta": meta,
        "payload": payload,
    }
    content_hash = _sha256_hex(_canonical_json(canonical))
    identifier = f"res:{content_hash[:16]}"
    return Resource(
        identifier=identifier,
        meta=meta,
        payload=payload,
        integrity={"content_hash": content_hash, "algo": "sha256"},
        extensions={},
    )


def _validate_event_v1_proposal(proposal: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    extraction = proposal.get("extraction", {})
    evidence = proposal.get("evidence_spans", {})
    required = schema.get("required", [])

    missing = [f for f in required if f not in extraction]
    if missing:
        raise AssertionError(f"Missing required fields: {missing}")

    for field in required:
        span = evidence.get(field, {})
        if span.get("start", -1) < 0 or span.get("end", -1) < 0:
            raise AssertionError(f"Missing/invalid evidence span for required field: {field}")

    return {
        "ok": True,
        "schema_id": "Event.v1",
        "extraction": extraction,
        "evidence_spans": evidence,
        "confidence": proposal.get("confidence", 0.0),
    }


def _update_schema_usage_metrics(context, schema_id: str, confidence: float) -> None:
    schema_usage = getattr(context, "schema_usage", None)
    if schema_usage is None:
        context.schema_usage = {}

    rec = context.schema_usage.get(
        schema_id,
        {
            "schema_id": schema_id,
            "successful_validations": 0,
            "avg_confidence": 0.0,
            "last_used_at": None,
        },
    )
    prev_n = rec["successful_validations"]
    new_n = prev_n + 1
    rec["avg_confidence"] = (rec["avg_confidence"] * prev_n + confidence) / new_n
    rec["successful_validations"] = new_n
    rec["last_used_at"] = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    context.schema_usage[schema_id] = rec


# -------------------------
# Given steps (infrastructure)
# -------------------------


@given("an append-only Resource store")
def step_given_append_only_store(context):
    context.resource_store = AppendOnlyResourceStore()
    _initialize_pipeline_context(context)


@given("a sparse index")
def step_given_sparse_index(context):
    context.sparse_index = SparseIndex()


@given("an ontology registry")
def step_given_ontology_registry(context):
    context.ontology_registry: dict[str, Any] = {}


@given("a schema registry with versioning")
def step_given_schema_registry(context):
    # schema_id -> dict(definition)
    context.schema_registry: dict[str, dict[str, Any]] = {}


@given("a dense interpreter configured for schema proposals")
def step_given_dense_interpreter(context):
    context.dense_interpreter = DenseInterpreterStub()


# -------------------------
# Given steps (domain data)
# -------------------------


@given('an ontology "core" with concepts:')
def step_given_ontology_core(context):
    # context.text holds the triple-quoted block
    context.ontology_registry["core"] = json.loads(context.text)


@given('a schema "Event.v1" mapped to ontology "core" with required fields:')
def step_given_schema_event_v1(context):
    schema_def = json.loads(context.text)
    schema_def["ontology"] = "core"
    context.schema_registry["Event.v1"] = schema_def


@given("a Dublin Core Resource with:")
def step_given_dc_resource_table(context):
    # Table has keys like dc:type, dc:created, dc:source, dc:format
    dc = {}
    for row in context.table:
        # behave tables expose row['<header>']
        # here the headers are the left column names, so use row.cells
        # row.cells -> [key, value]
        key = row.cells[0].strip()
        val = row.cells[1].strip()
        dc[key] = val

    context._pending_dc = dc
    context._pending_payload_text = None


@given("with payload text:")
def step_given_payload_text(context):
    context._pending_payload_text = context.text.strip("\n")


# -------------------------
# When steps (pipeline)
# -------------------------


@when("I ingest the Resource")
def step_when_ingest_resource(context):
    dc = getattr(context, "_pending_dc", None) or {}
    payload_text = getattr(context, "_pending_payload_text", None)
    if payload_text is None:
        raise AssertionError("No payload text provided for ingestion.")

    resource = _build_ingested_resource(context, dc=dc, payload_text=payload_text)

    context.resource_store.append(resource)
    context._last_persisted_resource = resource
    context._last_ingested_resource = resource


@when('I request a schema proposal from the dense interpreter using ontology "core"')
def step_when_request_schema_proposal(context):
    res: Resource = context._last_ingested_resource
    if not res:
        raise AssertionError("No ingested Resource to propose schema for.")

    # For the happy path, dense proposes Event.v1
    schema_id = "Event.v1"
    proposal = context.dense_interpreter.propose(
        payload_text=res.payload.get("text", ""),
        schema_id=schema_id,
        dc_created=res.meta.get("dc", {}).get("dc:created", "2026-02-14T10:00:00Z"),
    )
    context._last_proposal = proposal


@when('I validate the proposal against the ontology "core" and schema "Event.v1"')
def step_when_validate_proposal(context):
    proposal = getattr(context, "_last_proposal", None)
    if not proposal:
        raise AssertionError("No proposal to validate.")

    schema = context.schema_registry.get("Event.v1")
    if not schema:
        raise AssertionError('Schema "Event.v1" not found in registry.')

    context._last_validation = _validate_event_v1_proposal(proposal=proposal, schema=schema)


@when("I materialize a structured Artifact from the validated extraction")
def step_when_materialize_artifact(context):
    validation = getattr(context, "_last_validation", None)
    if not validation or not validation.get("ok"):
        raise AssertionError("Validation missing or failed; cannot materialize artifact.")

    source_res: Resource = context._last_ingested_resource
    schema_id = validation["schema_id"]
    extraction = validation["extraction"]
    evidence = validation["evidence_spans"]

    # Create an Artifact as a new immutable Resource
    meta = {
        "dc": {
            "dc:type": "Event",
            "dc:created": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
            "dc:source": "semanticng:materializer",
            "dc:format": "application/json",
        },
        "semanticng": {
            "schema_id": schema_id,
            "source_identifier": source_res.identifier,
        },
    }
    stable_ids = _derive_context_stable_ids(context)
    payload = {
        "extraction": extraction,
        "evidence_spans": evidence,
        "source_identifier": source_res.identifier,
        "schema_id": schema_id,
        "confidence": validation.get("confidence", 0.0),
    }
    if stable_ids:
        payload.update(stable_ids)
        meta.setdefault("semanticng", {}).update(stable_ids)
    canonical = {"meta": meta, "payload": payload}
    content_hash = _sha256_hex(_canonical_json(canonical))
    identifier = f"art:{content_hash[:16]}"

    artifact = Resource(
        identifier=identifier,
        meta=meta,
        payload=payload,
        integrity={"content_hash": content_hash, "algo": "sha256"},
        extensions={},
    )

    context.resource_store.append(artifact)
    context._last_persisted_resource = artifact
    context._last_artifact_resource = artifact

    _update_schema_usage_metrics(
        context=context,
        schema_id=schema_id,
        confidence=float(validation.get("confidence", 0.0)),
    )


@when("I update the sparse index from the persisted Artifact")
def step_when_update_sparse_index(context):
    art: Resource = context._last_artifact_resource
    if not art:
        raise AssertionError("No artifact resource to index.")

    # Build searchable text from extraction + selected metadata
    extraction = (art.payload or {}).get("extraction", {})
    searchable_parts = []

    # include key semantic fields
    for k in ["name", "location", "organizer", "startDate"]:
        v = extraction.get(k)
        if v:
            searchable_parts.append(str(v))

    # include raw payload source text too if needed later (not required here)
    # But for this happy path, extraction fields suffice.
    searchable_text = " ".join(searchable_parts)

    context.sparse_index.add(art.identifier, searchable_text)


# -------------------------
# Then steps (assertions)
# -------------------------


@then("the Resource MUST be persisted immutably with an integrity content_hash")
def step_then_resource_persisted_with_hash(context):
    res: Resource = context._last_persisted_resource
    assert res is not None, "No persisted resource found."
    assert isinstance(res.integrity, dict), "integrity must be a dict."
    assert "content_hash" in res.integrity, "integrity.content_hash missing."
    assert res.integrity["content_hash"], "integrity.content_hash empty."
    assert res.identifier, "resource identifier missing."


@then("the proposal MUST include a schema_id and a structured extraction")
def step_then_proposal_has_schema_and_extraction(context):
    proposal = getattr(context, "_last_proposal", None)
    assert proposal is not None, "No proposal found."
    assert "schema_id" in proposal, "proposal.schema_id missing."
    assert "extraction" in proposal and isinstance(proposal["extraction"], dict), (
        "proposal.extraction missing/invalid."
    )


@then("the proposal MUST cite evidence spans from the payload text")
def step_then_proposal_has_evidence_spans(context):
    proposal = getattr(context, "_last_proposal", None)
    assert proposal is not None, "No proposal found."
    spans = proposal.get("evidence_spans")
    assert isinstance(spans, dict) and spans, "proposal.evidence_spans missing/empty."

    # Ensure at least required fields have non-negative spans
    for key in ["name", "startDate"]:
        span = spans.get(key, {})
        assert span.get("start", -1) >= 0 and span.get("end", -1) >= 0, (
            f"Invalid evidence span for {key}"
        )


@then('the proposed schema_id MUST be "Event.v1"')
def step_then_proposed_schema_is_event_v1(context):
    proposal = getattr(context, "_last_proposal", None)
    assert proposal is not None, "No proposal found."
    assert proposal.get("schema_id") == "Event.v1", (
        f"Expected Event.v1, got {proposal.get('schema_id')}"
    )


@then("validation MUST succeed")
def step_then_validation_succeeds(context):
    val = getattr(context, "_last_validation", None)
    assert val is not None and val.get("ok") is True, "Validation did not succeed."


@then('the extracted fields MUST satisfy required fields for "Event.v1"')
def step_then_required_fields_present(context):
    val = getattr(context, "_last_validation", None)
    assert val and val.get("ok"), "No successful validation."
    schema = context.schema_registry["Event.v1"]
    required = schema.get("required", [])
    extraction = val.get("extraction", {})
    missing = [f for f in required if f not in extraction]
    assert not missing, f"Missing required fields: {missing}"


@then("the Artifact MUST be persisted as a new immutable Resource")
def step_then_artifact_persisted(context):
    art: Resource = context._last_artifact_resource
    assert art is not None, "Artifact not persisted."
    assert art.integrity.get("content_hash"), "Artifact content_hash missing."
    assert art.identifier.startswith("art:"), (
        f"Expected artifact id to start with art:, got {art.identifier}"
    )


@then('the Artifact dc:type MUST be "Event"')
def step_then_artifact_dc_type_event(context):
    art: Resource = context._last_artifact_resource
    dc = (art.meta or {}).get("dc", {})
    assert dc.get("dc:type") == "Event", f"Expected dc:type Event, got {dc.get('dc:type')}"


@then("the Artifact MUST include a link to the source Resource identifier")
def step_then_artifact_links_source(context):
    art: Resource = context._last_artifact_resource
    source_id = ((art.meta or {}).get("semanticng", {}) or {}).get("source_identifier")
    assert source_id, "Artifact missing semanticng.source_identifier"
    assert source_id == context._last_ingested_resource.identifier, (
        "Artifact source_identifier does not match ingested resource."
    )


@then("the Artifact MUST include evidence spans for each extracted field")
def step_then_artifact_has_evidence_per_field(context):
    art: Resource = context._last_artifact_resource
    extraction = (art.payload or {}).get("extraction", {})
    evidence = (art.payload or {}).get("evidence_spans", {})
    assert isinstance(evidence, dict) and evidence, "Artifact evidence_spans missing/empty."
    for field in extraction.keys():
        assert field in evidence, f"Missing evidence span for extracted field: {field}"


@then("the sparse index MUST contain the Artifact identifier")
def step_then_sparse_index_contains_artifact(context):
    art: Resource = context._last_artifact_resource
    assert art.identifier in context.sparse_index.docs, "Artifact not present in sparse index docs."


@then('searching for "hack night" MUST return the Artifact in the top results')
def step_then_search_hack_night_returns_artifact(context):
    art: Resource = context._last_artifact_resource
    results = context.sparse_index.search("hack night", top_k=5)
    assert art.identifier in results, (
        f"Artifact not found in top results for 'hack night'. Got: {results}"
    )


@then('searching for "Maria 01" MUST return the Artifact in the top results')
def step_then_search_maria01_returns_artifact(context):
    art: Resource = context._last_artifact_resource
    results = context.sparse_index.search("Maria 01", top_k=5)
    assert art.identifier in results, (
        f"Artifact not found in top results for 'Maria 01'. Got: {results}"
    )


@then('schema usage metrics MUST be updated for "Event.v1"')
def step_then_schema_usage_updated(context):
    usage = getattr(context, "schema_usage", {})
    assert "Event.v1" in usage, "No schema usage record for Event.v1"
    assert usage["Event.v1"]["successful_validations"] >= 1, (
        "successful_validations not incremented"
    )


@then("the schema usage record MUST include:")
def step_then_schema_usage_record_includes_metrics(context):
    usage = getattr(context, "schema_usage", {})
    rec = usage.get("Event.v1")
    assert rec, "No schema usage record for Event.v1"

    required_metrics = [row.cells[0].strip() for row in context.table]
    for m in required_metrics:
        assert m in rec, f"Missing metric '{m}' in schema usage record."
