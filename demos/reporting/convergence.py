from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Callable

from pydantic import BaseModel, Field

from demos.run_scenario_sessions import ScenarioSessionArtifact, ScenarioSessionBatch
from state_renormalization.engine import replay_projection_analytics


class SessionConvergencePoint(BaseModel):
    session_id: str
    scenario_id: str
    correction_count: int
    correction_cost_total: float
    correction_cost_mean: float


class ScenarioPackConvergence(BaseModel):
    scenario_pack: str
    session_count: int
    halt_frequency: float
    intervention_frequency: float
    correction_cost_total_trend: list[float] = Field(default_factory=list)
    correction_cost_mean_trend: list[float] = Field(default_factory=list)
    correction_count_trend: list[int] = Field(default_factory=list)
    session_points: list[SessionConvergencePoint] = Field(default_factory=list)


class ConvergenceReport(BaseModel):
    generated_at_iso: str
    source_sessions_path: str
    total_sessions: int
    total_halts: int
    total_interventions: int
    pack_reports: list[ScenarioPackConvergence] = Field(default_factory=list)


def load_scenario_session_batch(path: str | Path) -> ScenarioSessionBatch:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return ScenarioSessionBatch.model_validate(payload)


def build_convergence_report(
    sessions_path: str | Path,
    *,
    replay_loader: Callable[[str | Path], object] = replay_projection_analytics,
) -> ConvergenceReport:
    batch = load_scenario_session_batch(sessions_path)

    per_pack_sessions: dict[str, list[tuple[ScenarioSessionArtifact, SessionConvergencePoint, int]]] = defaultdict(list)
    total_halts = 0
    total_interventions = 0

    for session in batch.sessions:
        replay = replay_loader(session.prediction_log_path)
        analytics = replay.analytics_snapshot
        point = SessionConvergencePoint(
            session_id=session.session_id,
            scenario_id=session.scenario_id,
            correction_count=analytics.correction_count,
            correction_cost_total=analytics.correction_cost_total,
            correction_cost_mean=analytics.correction_cost_mean,
        )
        total_halts += analytics.halt_count
        total_interventions += session.intervention_count
        per_pack_sessions[session.scenario_pack].append((session, point, analytics.halt_count))

    pack_reports: list[ScenarioPackConvergence] = []
    for pack_name in sorted(per_pack_sessions):
        rows = per_pack_sessions[pack_name]
        session_points = [row[1] for row in rows]
        session_count = len(session_points)
        halt_frequency = sum(row[2] for row in rows) / float(session_count) if session_count else 0.0
        intervention_frequency = sum(row[0].intervention_count for row in rows) / float(session_count) if session_count else 0.0
        pack_reports.append(
            ScenarioPackConvergence(
                scenario_pack=pack_name,
                session_count=session_count,
                halt_frequency=halt_frequency,
                intervention_frequency=intervention_frequency,
                correction_cost_total_trend=[point.correction_cost_total for point in session_points],
                correction_cost_mean_trend=[point.correction_cost_mean for point in session_points],
                correction_count_trend=[point.correction_count for point in session_points],
                session_points=session_points,
            )
        )

    return ConvergenceReport(
        generated_at_iso=batch.generated_at_iso,
        source_sessions_path=str(Path(sessions_path)),
        total_sessions=len(batch.sessions),
        total_halts=total_halts,
        total_interventions=total_interventions,
        pack_reports=pack_reports,
    )


def write_convergence_report(*, sessions_path: str | Path, output_path: str | Path) -> Path:
    report = build_convergence_report(sessions_path)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report.model_dump(mode="json"), indent=2) + "\n", encoding="utf-8")
    return out
