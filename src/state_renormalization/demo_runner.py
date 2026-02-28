from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from state_renormalization.invariants import (
    Flow,
    InvariantId,
    default_check_context,
    run_checkers,
)


@dataclass(frozen=True)
class TurnExecution:
    turn_index: int
    prediction_issued: bool
    evidence_used: list[dict[str, str]]
    intervention_events: list[dict[str, Any]]
    invariant_checks: list[dict[str, Any]]
    outcome: str
    correction_metric: float


@dataclass(frozen=True)
class SessionExecution:
    context: str
    session_id: str
    turns: list[TurnExecution]


def load_scenario_packs(packs_dir: Path) -> list[dict[str, Any]]:
    packs: list[dict[str, Any]] = []
    for path in sorted(packs_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["_source"] = str(path)
        packs.append(payload)
    return packs


def _normalize_events(raw_events: list[Any]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for event in raw_events:
        if isinstance(event, str):
            events.append({"type": event})
        elif isinstance(event, dict):
            events.append({str(k): v for k, v in event.items()})
    return events


def run_session(pack: dict[str, Any]) -> SessionExecution:
    current_predictions: dict[str, dict[str, Any]] = {}
    turns: list[TurnExecution] = []

    for turn_index, turn in enumerate(pack.get("turns", []), start=1):
        prediction_key = str(turn.get("prediction_key") or f"turn:{turn_index}")
        prediction_issued = bool(turn.get("prediction_issued", True))
        prediction_log_available = bool(turn.get("prediction_log_available", True))
        evidence_used = [
            {"kind": str(item.get("kind", "unknown")), "ref": str(item.get("ref", ""))}
            for item in turn.get("evidence_used", [])
            if isinstance(item, dict)
        ]
        intervention_events = _normalize_events(list(turn.get("intervention_events", [])))

        if prediction_issued:
            current_predictions[prediction_key] = {
                "key": prediction_key,
                "evidence_refs": evidence_used,
            }

        pre_ctx = default_check_context(
            scope=pack["context"],
            prediction_key=prediction_key,
            current_predictions=current_predictions,
            prediction_log_available=prediction_log_available,
            just_written_prediction=None,
        )
        pre_outcomes = run_checkers(
            gate="pre-consume",
            ctx=pre_ctx,
            invariant_ids=(InvariantId.PREDICTION_AVAILABILITY,),
        )

        post_written = None
        if prediction_issued:
            post_written = {
                "key": prediction_key,
                "evidence_refs": evidence_used,
            }

        post_ctx = default_check_context(
            scope=pack["context"],
            prediction_key=prediction_key,
            current_predictions=current_predictions,
            prediction_log_available=prediction_log_available,
            just_written_prediction=post_written,
        )
        post_outcomes = run_checkers(
            gate="post-write",
            ctx=post_ctx,
            invariant_ids=(InvariantId.EVIDENCE_LINK_COMPLETENESS,),
        )

        all_outcomes = [*pre_outcomes, *post_outcomes]
        halt = any(outcome.flow == Flow.STOP for outcome in all_outcomes)
        issue = any(not outcome.passed for outcome in all_outcomes) and not halt
        warn = bool(intervention_events) and not halt and not issue

        expected_value = float(turn.get("expected_value", 0.0))
        observed_value = float(turn.get("observed_value", expected_value))
        correction_metric = abs(expected_value - observed_value)

        outcome = "halt" if halt else "issue" if issue else "warn" if warn else "ok"

        turns.append(
            TurnExecution(
                turn_index=turn_index,
                prediction_issued=prediction_issued,
                evidence_used=evidence_used,
                intervention_events=intervention_events,
                invariant_checks=[
                    {
                        "invariant_id": outcome_item.invariant_id.value,
                        "passed": outcome_item.passed,
                        "flow": outcome_item.flow.value,
                        "code": outcome_item.code,
                    }
                    for outcome_item in all_outcomes
                ],
                outcome=outcome,
                correction_metric=correction_metric,
            )
        )

    return SessionExecution(context=str(pack["context"]), session_id=str(pack["session_id"]), turns=turns)


def summarize(executions: list[SessionExecution]) -> dict[str, float]:
    total_checks = 0
    passing_checks = 0
    total_turns = 0
    intervention_turns = 0
    halt_turn_indices: list[tuple[list[TurnExecution], int]] = []
    correction_values: list[float] = []

    for execution in executions:
        for idx, turn in enumerate(execution.turns):
            total_turns += 1
            correction_values.append(turn.correction_metric)
            if turn.intervention_events:
                intervention_turns += 1
            for check in turn.invariant_checks:
                total_checks += 1
                if check["passed"]:
                    passing_checks += 1
            if turn.outcome == "halt":
                halt_turn_indices.append((execution.turns, idx))

    invariant_pass_rate = (passing_checks / total_checks) if total_checks else 0.0
    intervention_rate = (intervention_turns / total_turns) if total_turns else 0.0
    correction_trend = (correction_values[-1] - correction_values[0]) if len(correction_values) > 1 else 0.0

    recoveries = 0
    for turns, halt_idx in halt_turn_indices:
        if any(next_turn.outcome != "halt" for next_turn in turns[halt_idx + 1 :]):
            recoveries += 1
    recovery_success = (recoveries / len(halt_turn_indices)) if halt_turn_indices else 1.0

    return {
        "invariant_pass_rate": round(invariant_pass_rate, 4),
        "intervention_rate": round(intervention_rate, 4),
        "correction_trend": round(correction_trend, 4),
        "recovery_success_after_halts": round(recovery_success, 4),
    }


def run_packs(packs_dir: Path) -> dict[str, Any]:
    packs = load_scenario_packs(packs_dir)
    executions = [run_session(pack) for pack in packs]
    return {
        "sessions": [
            {
                "context": execution.context,
                "session_id": execution.session_id,
                "turns": [
                    {
                        "turn_index": turn.turn_index,
                        "prediction_issued": turn.prediction_issued,
                        "evidence_used": turn.evidence_used,
                        "intervention_events": turn.intervention_events,
                        "invariant_checks": turn.invariant_checks,
                        "halt_issue_warn_outcome": turn.outcome,
                        "correction_metric": turn.correction_metric,
                    }
                    for turn in execution.turns
                ],
            }
            for execution in executions
        ],
        "summary_metrics": summarize(executions),
    }
