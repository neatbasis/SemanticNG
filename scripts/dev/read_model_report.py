#!/usr/bin/env python3
from __future__ import annotations

import argparse

from state_renormalization.read_model import project_episode_scope_read_model_json


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Render episode/scope read-model report from append-only logs."
    )
    parser.add_argument("--episode-log", required=True, help="Path to episodes JSONL log")
    parser.add_argument("--prediction-log", required=True, help="Path to predictions JSONL log")
    parser.add_argument("--episode-id", required=True, help="Episode identifier")
    parser.add_argument("--scope", required=True, help="Scope key to reconstruct")
    args = parser.parse_args()

    report = project_episode_scope_read_model_json(
        episode_log_path=args.episode_log,
        prediction_log_path=args.prediction_log,
        episode_id=args.episode_id,
        scope=args.scope,
    )
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
