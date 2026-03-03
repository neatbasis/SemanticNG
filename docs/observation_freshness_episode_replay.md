# Observation Freshness Intervention Episode (End-to-End)

## Problem
A decision is about to proceed, but the latest `user_utterance` observation may be stale.

## Decision
1. **Input observation** is ingested into the episode.
2. **Invariant gate** runs in mission loop (`pre-decision`, `post-observation`, `pre-output`).
3. **Policy decision** evaluates observation freshness:
   - `continue` when fresh
   - `ask_request` when missing/stale/invalid timestamp
   - `hold` when an ask request is already outstanding

## Evidence
The episode stores auditable artifacts:
- `observation_freshness_decision` (contract-serialized decision + rationale + `evaluated_at_iso`)
- `observation_freshness_ask_request` when human input is requested
- `invariant_outcomes` from gate evaluation

## Replay
Use `replay_observation_freshness_episode(...)` to replay the exact freshness decision from the recorded episode artifact.

Replay is deterministic because it reuses the recorded `evaluated_at_iso` and compares the replayed decision against the original contract payload. A divergence raises an error; a match appends `observation_freshness_replay` with `status: "match"`.
