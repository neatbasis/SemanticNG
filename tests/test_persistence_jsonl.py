# tests/test_persistence_jsonl.py
from __future__ import annotations

import json
from pathlib import Path

from state_renormalization.adapters.persistence import append_jsonl, read_jsonl


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
