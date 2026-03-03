from __future__ import annotations

import json
from pathlib import Path

from state_renormalization.adapters.persistence import iter_projection_lineage_records, read_jsonl


def _as_str(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _collect_prediction_used(
    *,
    prediction_log_path: str | Path,
    episode_id: str,
    scope: str,
) -> dict[str, object] | None:
    latest: dict[str, object] | None = None
    for row in iter_projection_lineage_records(prediction_log_path):
        kind = row.get("event_kind")
        if kind not in {"prediction", "prediction_record"}:
            continue
        if row.get("scope_key") != scope:
            continue
        row_episode_id = row.get("episode_id")
        if isinstance(row_episode_id, str) and row_episode_id != episode_id:
            continue
        latest = {
            "prediction_id": _as_str(row.get("prediction_id")),
            "scope_key": _as_str(row.get("scope_key")),
            "prediction_key": _as_str(row.get("prediction_key")),
            "expectation": row.get("expectation"),
            "issued_at_iso": _as_str(row.get("issued_at_iso")),
            "evidence_refs": row.get("evidence_refs")
            if isinstance(row.get("evidence_refs"), list)
            else [],
        }
    return latest


def project_episode_scope_read_model(
    *,
    episode_log_path: str | Path,
    prediction_log_path: str | Path,
    episode_id: str,
    scope: str,
) -> dict[str, object]:
    selected_episode: dict[str, object] | None = None
    for _, row in read_jsonl(episode_log_path):
        if row.get("episode_id") == episode_id:
            selected_episode = row
            break

    if selected_episode is None:
        raise ValueError(f"episode_id not found in episode log: {episode_id}")

    artifacts = selected_episode.get("artifacts")
    if not isinstance(artifacts, list):
        artifacts = []

    scoped_invariants = [
        item
        for item in artifacts
        if isinstance(item, dict)
        and item.get("artifact_kind") == "invariant_outcomes"
        and item.get("scope") == scope
    ]

    if not scoped_invariants:
        raise ValueError(f"scope not found for episode_id={episode_id}: {scope}")

    latest_invariant = scoped_invariants[-1]

    checks = latest_invariant.get("invariant_checks")
    checks_out: list[dict[str, object]] = []
    evidence_refs: list[dict[str, str]] = []
    if isinstance(checks, list):
        for check in checks:
            if not isinstance(check, dict):
                continue
            checks_out.append(
                {
                    "gate_point": _as_str(check.get("gate_point")),
                    "invariant_id": _as_str(check.get("invariant_id")),
                    "passed": bool(check.get("passed")),
                    "flow": _as_str(check.get("flow")),
                    "code": _as_str(check.get("code")),
                    "reason": _as_str(check.get("reason")),
                }
            )
            check_evidence = check.get("evidence")
            if isinstance(check_evidence, list):
                for ref in check_evidence:
                    if (
                        isinstance(ref, dict)
                        and isinstance(ref.get("kind"), str)
                        and isinstance(ref.get("ref"), str)
                    ):
                        evidence_refs.append({"kind": ref["kind"], "ref": ref["ref"]})

    kind = _as_str(latest_invariant.get("kind")) or "unknown"
    halt = latest_invariant.get("halt") if isinstance(latest_invariant.get("halt"), dict) else None
    halt_evidence_ref = latest_invariant.get("halt_evidence_ref")
    if isinstance(halt_evidence_ref, dict):
        kind_ref = halt_evidence_ref.get("kind")
        row_ref = halt_evidence_ref.get("ref")
        if isinstance(kind_ref, str) and isinstance(row_ref, str):
            evidence_refs.append({"kind": kind_ref, "ref": row_ref})

    if isinstance(halt, dict):
        halt_evidence = halt.get("evidence")
        if isinstance(halt_evidence, list):
            for ref in halt_evidence:
                if (
                    isinstance(ref, dict)
                    and isinstance(ref.get("kind"), str)
                    and isinstance(ref.get("ref"), str)
                ):
                    evidence_refs.append({"kind": ref["kind"], "ref": ref["ref"]})

    prediction_used = _collect_prediction_used(
        prediction_log_path=prediction_log_path,
        episode_id=episode_id,
        scope=scope,
    )

    if prediction_used is not None:
        prediction_evidence = prediction_used.get("evidence_refs")
        if isinstance(prediction_evidence, list):
            for ref in prediction_evidence:
                if (
                    isinstance(ref, dict)
                    and isinstance(ref.get("kind"), str)
                    and isinstance(ref.get("ref"), str)
                ):
                    evidence_refs.append({"kind": ref["kind"], "ref": ref["ref"]})

    policy_decision = selected_episode.get("policy_decision")
    if not isinstance(policy_decision, dict):
        policy_decision = {}

    if kind == "halt" and isinstance(halt, dict):
        rationale = {
            "outcome": "halt",
            "reason": _as_str(halt.get("reason")),
            "invariant_id": _as_str(halt.get("invariant_id")),
            "retryability": halt.get("retryability"),
        }
    else:
        rationale = {
            "outcome": "continue",
            "reason": "all evaluated invariants passed for selected scope",
            "invariant_id": None,
            "retryability": None,
        }

    return {
        "episode_id": episode_id,
        "scope": scope,
        "prediction_used": prediction_used,
        "invariants_evaluated": checks_out,
        "policy_decision": {
            "decision_id": _as_str(policy_decision.get("decision_id")),
            "hypothesis": _as_str(policy_decision.get("hypothesis")),
            "reason_codes": policy_decision.get("reason_codes")
            if isinstance(policy_decision.get("reason_codes"), list)
            else [],
            "channel": _as_str(policy_decision.get("channel")),
        },
        "halt_continue_rationale": rationale,
        "evidence_refs": evidence_refs,
    }


def project_episode_scope_read_model_json(
    *,
    episode_log_path: str | Path,
    prediction_log_path: str | Path,
    episode_id: str,
    scope: str,
) -> str:
    payload = project_episode_scope_read_model(
        episode_log_path=episode_log_path,
        prediction_log_path=prediction_log_path,
        episode_id=episode_id,
        scope=scope,
    )
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2)
