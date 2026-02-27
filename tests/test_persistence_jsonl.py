# tests/test_persistence_jsonl.py
from __future__ import annotations

import json
from pathlib import Path

from state_renormalization.adapters.persistence import append_halt, append_jsonl, read_jsonl


def test_append_and_read_jsonl_roundtrip(tmp_path: Path) -> None:
    p = tmp_path / "events.jsonl"

    append_jsonl(p, {"kind": "x", "n": 1})
    append_jsonl(p, {"kind": "x", "n": 2})

    rows = [rec for _, rec in read_jsonl(p)]
    assert rows == [{"kind": "x", "n": 1}, {"kind": "x", "n": 2}]

    # sanity: file is valid json-per-line
    raw_lines = p.read_text(encoding="utf-8").splitlines()
    for ln in raw_lines:
        json.loads(ln)


def test_append_halt_jsonl_roundtrip_and_evidence_ref_format(tmp_path: Path) -> None:
    p = tmp_path / "halts.jsonl"

    ref = append_halt(p, {"halt_id": "halt:1", "stage": "post_write", "reason": "x"})

    (meta, rec), = list(read_jsonl(p))
    assert rec["halt_id"] == "halt:1"
    assert rec["stage"] == "post_write"
    assert meta["lineno"] == 1
    assert ref == {"kind": "jsonl", "ref": "halts.jsonl@1"}
    assert "@" in ref["ref"]
    file_name, line_no = ref["ref"].split("@", 1)
    assert file_name == "halts.jsonl"
    assert line_no == "1"


def test_append_jsonl_propagates_stable_ids_to_nested_events(tmp_path: Path) -> None:
    p = tmp_path / "events.jsonl"

    append_jsonl(
        p,
        {
            "kind": "episode",
            "stable_ids": {
                "feature_id": "feat_1",
                "scenario_id": "scn_1",
                "step_id": "stp_1",
            },
            "events": [
                {"kind": "step", "name": "Given x"},
                {"kind": "decision", "name": "choose y"},
            ],
        },
    )

    (_, rec), = list(read_jsonl(p))
    assert rec["feature_id"] == "feat_1"
    assert rec["events"][0]["feature_id"] == "feat_1"
    assert rec["events"][0]["scenario_id"] == "scn_1"
    assert rec["events"][0]["step_id"] == "stp_1"
    assert rec["events"][1]["feature_id"] == "feat_1"
