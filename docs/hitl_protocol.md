# HITL Protocol

This document defines the Human-in-the-Loop (HITL) protocol used by the engine when automated execution requires operator intervention.

## 1) Intervention request contract

`InterventionRequest` is emitted when the engine needs human guidance or authorization.

Required fields:

- `intervention_id`: stable id for the intervention cycle.
- `episode_id`, `conversation_id`, `turn_index`: episode linkage.
- `requested_at_iso`: UTC timestamp for request creation.
- `reason`: concise machine-readable or operator-readable reason.
- `prompt`: question/instruction shown to the operator.
- `context`: structured payload with relevant evidence.
- `timeout_rule`: `EscalationTimeoutRule` containing timeout/escalation policy.
- `timeout_count`: number of prior timeout rounds.
- `status`: initial status (`requested`).

## 2) Operator response contract

`OperatorResponse` is accepted to resume a paused loop.

Required fields:

- `intervention_id`, `episode_id`: request correlation.
- `response_type`: one of `approve`, `reject`, `override`, `request_more_context`, `ack_timeout`.
- `provided_at_iso`: UTC timestamp.
- `approved`: bool summary for quick policy checks.

Optional fields:

- `message`: freeform operator note.
- `override_payload`: machine-readable override values.
- `override_provenance`: required when `response_type=override`.

## 3) Escalation and timeout rules

`EscalationTimeoutRule` controls timeout handling:

- `timeout_seconds`: maximum wait for operator response.
- `max_timeouts_before_escalation`: escalation threshold.
- `escalation_target`: queue/user/team to escalate to.
- `on_timeout_status`: status emitted on non-escalating timeout.
- `on_escalation_status`: status emitted when threshold is exceeded.

Engine behavior:

1. If a request exists and no operator response is present, engine appends `intervention_event/pause` and returns early.
2. If `timeout_count > 0`, engine evaluates timeout and appends `intervention_event/timeout_evaluation` with either `timeout` or `escalated`.
3. On response, engine appends `intervention_event/resume` and continues execution.

## 4) Override provenance fields

`OverrideProvenance` tracks authority and auditability for operator overrides:

- `override_id`: stable id for the override record.
- `operator_id`: actor identifier.
- `operator_role`: operator authority role.
- `justification`: human rationale.
- `source_channel`: UI/system where override originated.
- `ticket_ref`: optional incident/task reference.
- `supersedes_decision_id`: optional policy decision superseded.
- `applied_at_iso`: UTC timestamp.

When `OperatorResponse.response_type == override`, provenance MUST be present.

## 5) Episode artifact events

The engine appends intervention lifecycle events to `Episode.artifacts`:

- `intervention_event` + `event_type=pause`
- `intervention_event` + `event_type=timeout_evaluation`
- `intervention_event` + `event_type=resume`
- `intervention_event` + `event_type=override_applied`

These events are designed for downstream audit pipelines and replay tooling.
