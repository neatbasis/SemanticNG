#!/usr/bin/env python3
import json
from pathlib import Path


def _load_json(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _validate_dod_manifest(data: dict) -> list[str]:
    errors: list[str] = []
    statuses = data.get("statuses")
    if not isinstance(statuses, list) or not all(isinstance(s, str) for s in statuses):
        errors.append("docs/dod_manifest.json: `statuses` must be a list[str].")
        statuses = []

    capabilities = data.get("capabilities")
    if not isinstance(capabilities, list):
        return errors + ["docs/dod_manifest.json: `capabilities` must be a list."]

    seen_ids: set[str] = set()
    for idx, cap in enumerate(capabilities):
        if not isinstance(cap, dict):
            errors.append(f"docs/dod_manifest.json: capabilities[{idx}] must be an object.")
            continue
        cap_id = cap.get("id")
        status = cap.get("status")
        if not isinstance(cap_id, str) or not cap_id.strip():
            errors.append(f"docs/dod_manifest.json: capabilities[{idx}].id must be a non-empty string.")
        elif cap_id in seen_ids:
            errors.append(f"docs/dod_manifest.json: duplicate capability id `{cap_id}`.")
        else:
            seen_ids.add(cap_id)
        if status not in statuses:
            errors.append(
                f"docs/dod_manifest.json: capability `{cap_id}` has status `{status}` not present in `statuses`.")

        pytest_commands = cap.get("pytest_commands")
        evidence_links = cap.get("ci_evidence_links")
        if not isinstance(pytest_commands, list) or not all(isinstance(c, str) for c in pytest_commands):
            errors.append(f"docs/dod_manifest.json: capability `{cap_id}` pytest_commands must be list[str].")
        if not isinstance(evidence_links, list) or not all(isinstance(e, dict) for e in evidence_links):
            errors.append(f"docs/dod_manifest.json: capability `{cap_id}` ci_evidence_links must be list[object].")

    return errors


def _validate_no_regression_budget(data: dict) -> list[str]:
    errors: list[str] = []
    done_ids = data.get("done_capability_ids")
    if not isinstance(done_ids, list) or not all(isinstance(item, str) for item in done_ids):
        errors.append("docs/no_regression_budget.json: `done_capability_ids` must be list[str].")

    waivers = data.get("waivers")
    if waivers is not None and not isinstance(waivers, list):
        errors.append("docs/no_regression_budget.json: `waivers` must be a list when present.")

    baseline_governance = data.get("baseline_update_governance")
    if not isinstance(baseline_governance, dict):
        errors.append(
            "docs/no_regression_budget.json: `baseline_update_governance` must be an object."
        )
    else:
        policy_doc = baseline_governance.get("policy_doc")
        metadata_file = baseline_governance.get("metadata_file")
        default_allowed = baseline_governance.get("default_allowed_regression")
        if not isinstance(policy_doc, str) or not policy_doc.strip():
            errors.append(
                "docs/no_regression_budget.json: baseline_update_governance.policy_doc must be a non-empty string."
            )
        if not isinstance(metadata_file, str) or not metadata_file.strip():
            errors.append(
                "docs/no_regression_budget.json: baseline_update_governance.metadata_file must be a non-empty string."
            )
        if default_allowed != 0:
            errors.append(
                "docs/no_regression_budget.json: baseline_update_governance.default_allowed_regression must be 0."
            )

    return errors


def _validate_no_regression_update_request(data: dict) -> list[str]:
    errors: list[str] = []
    if not isinstance(data.get("status"), str):
        errors.append("docs/no_regression_budget_update_request.json: `status` must be a string.")

    checklist = data.get("checklist")
    if not isinstance(checklist, dict):
        errors.append("docs/no_regression_budget_update_request.json: `checklist` must be an object.")

    timeboxed = data.get("timeboxed_exception")
    if not isinstance(timeboxed, dict):
        errors.append(
            "docs/no_regression_budget_update_request.json: `timeboxed_exception` must be an object."
        )

    return errors


def main() -> int:
    errors: list[str] = []
    errors.extend(_validate_dod_manifest(_load_json("docs/dod_manifest.json")))
    errors.extend(_validate_no_regression_budget(_load_json("docs/no_regression_budget.json")))
    errors.extend(
        _validate_no_regression_update_request(
            _load_json("docs/no_regression_budget_update_request.json")
        )
    )

    if errors:
        print("Governance docs schema validation failed:")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("Governance docs schema validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
