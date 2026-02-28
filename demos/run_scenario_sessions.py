from __future__ import annotations

import argparse
import json
from pathlib import Path

from pydantic import BaseModel, Field


class ScenarioSessionArtifact(BaseModel):
    """Persisted handle for a completed scenario session run."""

    session_id: str
    scenario_id: str
    scenario_pack: str
    prediction_log_path: str
    intervention_count: int = 0


class ScenarioSessionBatch(BaseModel):
    """Append-only payload contract consumed by replay/correction reporting."""

    generated_at_iso: str
    sessions: list[ScenarioSessionArtifact] = Field(default_factory=list)


def write_scenario_session_batch(*, output_path: str | Path, batch: ScenarioSessionBatch) -> Path:
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(batch.model_dump(mode="json"), indent=2) + "\n", encoding="utf-8")
    return out


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Persist scenario session batch metadata for convergence reporting.")
    parser.add_argument("--output", required=True, help="Path to write scenario session JSON artifact.")
    parser.add_argument(
        "--generated-at-iso",
        default="1970-01-01T00:00:00+00:00",
        help="Deterministic timestamp embedded in the persisted batch artifact.",
    )
    parser.add_argument(
        "--session",
        action="append",
        default=[],
        metavar="SESSION_ID,SCENARIO_ID,SCENARIO_PACK,PREDICTION_LOG_PATH[,INTERVENTION_COUNT]",
        help="Session tuple. Repeat for multiple sessions.",
    )
    return parser.parse_args()


def _parse_session_arg(raw: str) -> ScenarioSessionArtifact:
    parts = [part.strip() for part in raw.split(",")]
    if len(parts) not in {4, 5}:
        raise ValueError("--session must have 4 or 5 comma-separated fields")

    intervention_count = int(parts[4]) if len(parts) == 5 and parts[4] else 0
    return ScenarioSessionArtifact(
        session_id=parts[0],
        scenario_id=parts[1],
        scenario_pack=parts[2],
        prediction_log_path=parts[3],
        intervention_count=intervention_count,
    )


def main() -> int:
    args = _parse_args()
    batch = ScenarioSessionBatch(
        generated_at_iso=args.generated_at_iso,
        sessions=[_parse_session_arg(item) for item in args.session],
    )
    write_scenario_session_batch(output_path=args.output, batch=batch)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
