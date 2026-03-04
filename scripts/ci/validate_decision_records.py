from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = Path("docs/process/decision_record.schema.json")
DIRECTIVES_DIR = Path("docs/directives")
REQUIRED_CANONICAL_REFS = {
    "docs/dod_manifest.json",
    "docs/system_contract_map.md",
    "docs/process/quality_stage_commands.json",
}


@dataclass(frozen=True)
class RecordMeta:
    file_path: Path
    record_id: str
    record_date: date


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_required_fields(record: dict[str, Any], schema: dict[str, Any], path: Path) -> list[str]:
    errors: list[str] = []
    required = schema.get("required", [])
    if not isinstance(required, list):
        return [f"{path}: schema required list is invalid"]

    for field in required:
        if field not in record:
            errors.append(f"{path}: missing required field '{field}'")

    return errors


def _validate_canonical_refs(record: dict[str, Any], path: Path, root: Path) -> list[str]:
    errors: list[str] = []
    refs = record.get("canonical_refs")
    if not isinstance(refs, list) or not all(isinstance(item, str) for item in refs):
        return [f"{path}: canonical_refs must be a list of file paths"]

    ref_set = set(refs)
    missing = sorted(REQUIRED_CANONICAL_REFS - ref_set)
    for missing_ref in missing:
        errors.append(f"{path}: canonical_refs missing required reference '{missing_ref}'")

    for ref in refs:
        ref_path = root / ref
        if not ref_path.exists():
            errors.append(f"{path}: canonical_refs target does not exist '{ref}'")

    return errors


def _parse_record_meta(record: dict[str, Any], path: Path) -> tuple[RecordMeta | None, list[str]]:
    errors: list[str] = []
    record_id = record.get("id")
    raw_date = record.get("date")

    if not isinstance(record_id, str):
        errors.append(f"{path}: id must be a string")
    if not isinstance(raw_date, str):
        errors.append(f"{path}: date must be a string")

    if errors:
        return None, errors

    try:
        parsed_date = date.fromisoformat(raw_date)
    except ValueError:
        return None, [f"{path}: date must be ISO-8601 YYYY-MM-DD"]

    return RecordMeta(file_path=path, record_id=record_id, record_date=parsed_date), []


def validate_decision_records(root: Path = ROOT) -> list[str]:
    errors: list[str] = []

    schema_path = root / SCHEMA_PATH
    directives_dir = root / DIRECTIVES_DIR

    if not schema_path.exists():
        return [f"{schema_path}: schema file is missing"]
    if not directives_dir.exists():
        return [f"{directives_dir}: directives directory is missing"]

    schema = _load_json(schema_path)
    records: list[RecordMeta] = []
    seen_ids: dict[str, Path] = {}

    for record_path in sorted(directives_dir.glob("*.json")):
        record = _load_json(record_path)
        if not isinstance(record, dict):
            errors.append(f"{record_path}: record must be a JSON object")
            continue

        errors.extend(_validate_required_fields(record, schema, record_path))
        errors.extend(_validate_canonical_refs(record, record_path, root))

        meta, meta_errors = _parse_record_meta(record, record_path)
        errors.extend(meta_errors)
        if meta is None:
            continue

        if meta.record_id in seen_ids:
            errors.append(
                f"{record_path}: duplicate id '{meta.record_id}' already used by {seen_ids[meta.record_id]}"
            )
        else:
            seen_ids[meta.record_id] = record_path
            records.append(meta)

    records_sorted = sorted(records, key=lambda item: item.record_id)
    for previous, current in zip(records_sorted, records_sorted[1:]):
        if current.record_date < previous.record_date:
            errors.append(
                "non-monotonic date ordering: "
                f"{current.file_path} ({current.record_date.isoformat()}) is earlier than "
                f"{previous.file_path} ({previous.record_date.isoformat()})"
            )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate decision/directive JSON records")
    parser.add_argument("--root", type=Path, default=ROOT, help="Repository root path")
    args = parser.parse_args()

    errors = validate_decision_records(args.root)
    if errors:
        for error in errors:
            print(error)
        return 1

    print("Decision records validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
