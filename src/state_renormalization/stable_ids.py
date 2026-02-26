# state_renormalization/stable_ids.py
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


def _sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _canon(obj: Any) -> str:
    """
    Canonical JSON string (stable across runs) for hashing.
    """
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


@dataclass(frozen=True)
class StableIds:
    uri: str
    feature_id: str
    scenario_ids: Dict[str, str]          # key: scenario_key -> scenario_id
    step_ids: Dict[str, str]              # key: step_key -> step_id


def derive_stable_ids(gherkin_document: Dict[str, Any], *, uri: Optional[str] = None) -> StableIds:
    """
    Compute stable IDs for feature/scenarios/steps using deterministic hashing.
    Does NOT rely on gherkin-official's internal incremental IDs.
    """
    doc_uri = uri or gherkin_document.get("uri") or ""
    feature = gherkin_document.get("feature") or {}
    feature_name = feature.get("name") or ""
    feature_loc = feature.get("location") or {}
    f_line = feature_loc.get("line")
    f_col = feature_loc.get("column")

    # Feature ID: uri + feature name (+ location as tie-breaker)
    feature_key_obj = {
        "uri": doc_uri,
        "feature": feature_name,
        "line": f_line,
        "col": f_col,
    }
    feature_id = "feat_" + _sha256_hex(_canon(feature_key_obj))

    scenario_ids: Dict[str, str] = {}
    step_ids: Dict[str, str] = {}

    children = feature.get("children") or []
    for child in children:
        scenario = child.get("scenario")
        if not scenario:
            # Could also be background/rule/etc. Add later if needed.
            continue

        s_name = scenario.get("name") or ""
        s_keyword = scenario.get("keyword") or ""
        s_loc = scenario.get("location") or {}
        s_line = s_loc.get("line")
        s_col = s_loc.get("column")

        scenario_key_obj = {
            "feature_id": feature_id,
            "keyword": s_keyword,
            "name": s_name,
            "line": s_line,
            "col": s_col,
        }
        scenario_id = "scn_" + _sha256_hex(_canon(scenario_key_obj))

        # Scenario "key" is a deterministic string you can use in logs/debugging
        scenario_key = f"{s_keyword}:{s_name}@{s_line}:{s_col}"
        scenario_ids[scenario_key] = scenario_id

        steps = scenario.get("steps") or []
        for step in steps:
            st_text = step.get("text") or ""
            st_type = step.get("keywordType") or ""
            st_keyword = step.get("keyword") or ""
            st_loc = step.get("location") or {}
            st_line = st_loc.get("line")
            st_col = st_loc.get("column")

            step_key_obj = {
                "scenario_id": scenario_id,
                "keywordType": st_type,
                "keyword": st_keyword,
                "text": st_text,
                "line": st_line,
                "col": st_col,
            }
            step_id = "stp_" + _sha256_hex(_canon(step_key_obj))

            step_key = f"{scenario_key}::{st_type}:{st_text}@{st_line}:{st_col}"
            step_ids[step_key] = step_id

    return StableIds(
        uri=doc_uri,
        feature_id=feature_id,
        scenario_ids=scenario_ids,
        step_ids=step_ids,
    )
