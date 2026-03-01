# state_renormalization/adapters/persistence.py
from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError

from state_renormalization.contracts import (
    CapabilityAdapterGate,
    HaltPayloadValidationError,
    HaltRecord,
)

JsonObj = dict[str, Any]
PathLike = str | Path

PREDICTIONS_LOG_PATH = Path("artifacts/predictions.jsonl")
PREDICTION_RECORDS_LOG_PATH = Path("artifacts/prediction_records.jsonl")


def _to_jsonable(x: Any) -> Any:
    if x is None:
        return None
    if isinstance(x, BaseModel):
        return x.model_dump(mode="json")
    if is_dataclass(x) and not isinstance(x, type):
        return asdict(x)
    if isinstance(x, dict):
        return {str(k): _to_jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_to_jsonable(v) for v in x]
    return x


def _stable_ids_from_record(record: JsonObj) -> JsonObj:
    stable = record.get("stable_ids")
    out: JsonObj = {}
    if isinstance(stable, dict):
        for key in ("feature_id", "scenario_id", "step_id"):
            if isinstance(stable.get(key), str):
                out[key] = stable[key]

    for key in ("feature_id", "scenario_id", "step_id"):
        val = record.get(key)
        if isinstance(val, str):
            out[key] = val
    return out


def _inject_stable_ids(record: JsonObj) -> JsonObj:
    stable = _stable_ids_from_record(record)
    if not stable:
        return record

    out = {**stable, **record}

    for dict_key in ("embedding", "ontology_alignment", "elasticsearch_document", "index_document"):
        item = out.get(dict_key)
        if isinstance(item, dict):
            out[dict_key] = {**stable, **item}

    for list_key in (
        "events",
        "artifacts",
        "steps",
        "decisions",
        "embeddings",
        "ontology_alignments",
        "elasticsearch_documents",
        "index_documents",
    ):
        items = out.get(list_key)
        if not isinstance(items, list):
            continue
        enriched: list[Any] = []
        for item in items:
            if isinstance(item, dict):
                enriched.append({**stable, **item})
            else:
                enriched.append(item)
        out[list_key] = enriched

    return out


def append_jsonl(path: PathLike, record: Any) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    obj = _to_jsonable(record)
    if isinstance(obj, dict):
        obj = _inject_stable_ids(obj)

    # enforce "one JSON object per line"
    line = json.dumps(obj, ensure_ascii=False)
    with p.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def read_jsonl(path: PathLike) -> Iterator[tuple[JsonObj, JsonObj]]:
    """
    Yields (meta, obj) for each JSON object line.
    - meta includes line number and source path.
    - obj is the parsed dict (what your test wants as `rec`).
    """
    p = Path(path)
    with p.open("r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            s = line.strip()
            if not s:
                continue
            obj = json.loads(s)
            if not isinstance(obj, dict):
                raise ValueError(f"Expected JSON object on line {lineno}, got {type(obj).__name__}")
            meta: JsonObj = {"path": str(p), "lineno": lineno}
            yield meta, obj


def _enforce_adapter_gate(*, action: str, adapter_gate: CapabilityAdapterGate) -> None:
    if not adapter_gate.allowed:
        raise PermissionError(f"{action} denied: adapter gate is not allowed")


def append_prediction(
    path: PathLike = PREDICTIONS_LOG_PATH,
    record: Any = None,
    *,
    adapter_gate: CapabilityAdapterGate,
) -> JsonObj:
    _enforce_adapter_gate(action="append_prediction", adapter_gate=adapter_gate)
    if record is None:
        raise ValueError("append_prediction requires a prediction record")
    p = Path(path)
    next_offset = 1
    if p.exists():
        next_offset = len(p.read_text(encoding="utf-8").splitlines()) + 1

    append_jsonl(p, record)
    return {"kind": "jsonl", "ref": f"{p.name}@{next_offset}"}


def append_prediction_event(
    record: Any,
    *,
    adapter_gate: CapabilityAdapterGate,
    path: PathLike = PREDICTIONS_LOG_PATH,
    episode_id: str | None = None,
    conversation_id: str | None = None,
    turn_index: int | None = None,
) -> JsonObj:
    payload = _to_jsonable(record)
    if not isinstance(payload, dict):
        raise ValueError("append_prediction_event expects a dict-like prediction payload")

    event: JsonObj = {"event_kind": "prediction", **payload}
    if episode_id:
        event["episode_id"] = episode_id
    if conversation_id:
        event["conversation_id"] = conversation_id
    if turn_index is not None:
        event["turn_index"] = int(turn_index)

    return append_prediction(path=path, record=event, adapter_gate=adapter_gate)


def append_prediction_record_event(
    record: Any,
    *,
    adapter_gate: CapabilityAdapterGate,
    path: PathLike = PREDICTION_RECORDS_LOG_PATH,
    episode_id: str | None = None,
    conversation_id: str | None = None,
    turn_index: int | None = None,
) -> JsonObj:
    _enforce_adapter_gate(action="append_prediction_record_event", adapter_gate=adapter_gate)

    payload = _to_jsonable(record)
    if not isinstance(payload, dict):
        raise ValueError("append_prediction_record_event expects a dict-like prediction payload")

    event: JsonObj = {"event_kind": "prediction_record", **payload}
    if episode_id:
        event["episode_id"] = episode_id
    if conversation_id:
        event["conversation_id"] = conversation_id
    if turn_index is not None:
        event["turn_index"] = int(turn_index)

    return append_prediction(path=path, record=event, adapter_gate=adapter_gate)


def append_ask_outbox_request_event(
    record: Any,
    *,
    adapter_gate: CapabilityAdapterGate,
    path: PathLike = PREDICTIONS_LOG_PATH,
) -> JsonObj:
    _enforce_adapter_gate(action="append_ask_outbox_request_event", adapter_gate=adapter_gate)

    payload = _to_jsonable(record)
    if not isinstance(payload, dict):
        raise ValueError("append_ask_outbox_request_event expects a dict-like payload")

    return append_prediction(path=path, record=payload, adapter_gate=adapter_gate)


def append_ask_outbox_response_event(
    record: Any,
    *,
    adapter_gate: CapabilityAdapterGate,
    path: PathLike = PREDICTIONS_LOG_PATH,
) -> JsonObj:
    _enforce_adapter_gate(action="append_ask_outbox_response_event", adapter_gate=adapter_gate)

    payload = _to_jsonable(record)
    if not isinstance(payload, dict):
        raise ValueError("append_ask_outbox_response_event expects a dict-like payload")

    return append_prediction(path=path, record=payload, adapter_gate=adapter_gate)


def iter_projection_lineage_records(path: PathLike) -> Iterator[JsonObj]:
    """Yield append-only projection lineage rows that can be rehydrated.

    Includes prediction events and canonical halt payload rows.
    Excludes unknown event kinds and malformed/non-object JSONL rows.
    """
    p = Path(path)
    if not p.exists():
        return

    with p.open("r", encoding="utf-8") as handle:
        for line in handle:
            raw_line = line.strip()
            if not raw_line:
                continue

            try:
                raw = json.loads(raw_line)
            except json.JSONDecodeError:
                continue

            if not isinstance(raw, dict):
                continue

            kind = raw.get("event_kind")
            if kind in {
                "prediction_record",
                "prediction",
                "repair_proposal",
                "repair_resolution",
                "ask_outbox_request",
                "ask_outbox_response",
            }:
                yield raw
                continue

            # IMPORTANT:
            # - lineage iteration should be resilient (skip malformed rows)
            # - prefer strict Pydantic validation here so "halt" rows are guaranteed canonical
            try:
                yield HaltRecord.validate_payload(raw).to_canonical_payload()
            except Exception:
                continue


def _canonicalize_halt_payload(record: Any) -> JsonObj:
    """
    Convert a halt-ish object into the canonical persisted JSON payload.

    NOTE on exception semantics:
    - Use HaltRecord.validate_payload(...) here so persistence has "raw Pydantic" behavior
      (i.e. raises pydantic.ValidationError for malformed inputs), matching adapter tests.
    - Keep HaltRecord.from_payload(...) for "domain boundary" rehydration where you want
      HaltPayloadValidationError instead.
    """
    if isinstance(record, HaltRecord):
        return record.to_canonical_payload()

    if isinstance(record, dict):
        canonical = HaltRecord.from_payload(record).to_canonical_payload()
        stable_ids = {
            key: value
            for key in ("feature_id", "scenario_id", "step_id")
            if isinstance((value := record.get(key)), str)
        }
        return {**stable_ids, **canonical}

    # Convert non-dict inputs (dataclass/BaseModel/etc.) and validate strictly.
    payload = _to_jsonable(record)
    return HaltRecord.validate_payload(payload).to_canonical_payload()


def read_halt_record(record: JsonObj) -> HaltRecord:
    """Rehydrate a persisted halt artifact into a validated HaltRecord.

    Uses the domain boundary method (wraps into HaltPayloadValidationError).
    """
    return HaltRecord.from_payload(record)


def append_halt(path: PathLike, record: Any, *, adapter_gate: CapabilityAdapterGate) -> JsonObj:
    _enforce_adapter_gate(action="append_halt", adapter_gate=adapter_gate)
    p = Path(path)
    next_offset = 1
    if p.exists():
        next_offset = len(p.read_text(encoding="utf-8").splitlines()) + 1

    try:
        payload = _canonicalize_halt_payload(record)
        # Validate persistence/reload parity for explainability payload fields.
        HaltRecord.from_payload(payload)
    except HaltPayloadValidationError as exc:
        # persistence tests expect pydantic.ValidationError
        raise ValidationError.from_exception_data(
            "HaltRecord",
            [
                {
                    "loc": ("halt",),
                    "type": "value_error",
                    "input": record,
                    "ctx": {"error": str(exc)},
                }
            ],
        ) from exc

    append_jsonl(p, payload)
    return {"kind": "jsonl", "ref": f"{p.name}@{next_offset}"}
