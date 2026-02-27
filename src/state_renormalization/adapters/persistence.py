# state_renormalization/adapters/persistence.py
from __future__ import annotations

import json
from dataclasses import is_dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, Tuple, Union

from pydantic import BaseModel


JsonObj = Dict[str, Any]
PathLike = Union[str, Path]


def _to_jsonable(x: Any) -> Any:
    if x is None:
        return None
    if isinstance(x, BaseModel):
        return x.model_dump(mode="json")
    if is_dataclass(x):
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

    for list_key in ("events", "artifacts", "steps", "decisions"):
        items = out.get(list_key)
        if not isinstance(items, list):
            continue
        enriched = []
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


def read_jsonl(path: PathLike) -> Iterator[Tuple[JsonObj, JsonObj]]:
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


# TODO: This prevents weird non-dict JSON from exploding later when you call raw.get(...).
#raw = json.loads(line)
#if not isinstance(raw, dict):
#    if strict:
#        raise TypeError(f"Expected dict JSON object on line {line_no}")
#    yield line_no, {
#        "kind": "json_type_error",
#        "error": f"Expected object, got {type(raw).__name__}",
#        "raw": raw,
#        "line_no": line_no,
#    }
#    continue


def append_prediction(path: PathLike, record: Any) -> JsonObj:
    p = Path(path)
    next_offset = 1
    if p.exists():
        next_offset = len(p.read_text(encoding="utf-8").splitlines()) + 1

    append_jsonl(p, record)
    return {"kind": "jsonl", "ref": f"{p.name}@{next_offset}"}


def append_halt(path: PathLike, record: Any) -> JsonObj:
    p = Path(path)
    next_offset = 1
    if p.exists():
        next_offset = len(p.read_text(encoding="utf-8").splitlines()) + 1

    append_jsonl(p, record)
    return {"kind": "jsonl", "ref": f"{p.name}@{next_offset}"}
