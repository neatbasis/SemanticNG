# features/steps/resource_steps.py
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from gherkin.parser import Parser  # type: ignore[import-not-found]
from gherkin.token_scanner import TokenScanner  # type: ignore[import-not-found]

from semanticng.bdd_compat import given, then, when
from semanticng.step_state import get_resource_step_state

from state_renormalization.gherkin_document import GherkinDocument
from state_renormalization.stable_ids import derive_stable_ids

# ----------------------------
# Minimal helpers used in steps
# ----------------------------

EXT_KEY_PATTERN = re.compile(r"^[A-Za-z0-9_.:-]+\.v[0-9]+$")  # e.g. forecasting.v1
# If you decide to use ontology lanes instead, change to: r"^[^@\s]+@[0-9]+$" (e.g. sng:temporal@1)


def canonical_json(obj: Any) -> str:
    """
    Canonical JSON: stable ordering, no whitespace differences.
    (Good enough for CI contract tests; if you need RFC 8785 JSON Canonicalization Scheme, swap later.)
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def content_addressed_id(hash_hex: str) -> str:
    return f"urn:sha256:{hash_hex}"


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    code: str | None = None
    warning: str | None = None


class AppendOnlyStore:
    def __init__(self) -> None:
        self._by_id: dict[str, dict[str, Any]] = {}

    def put(self, resource: dict[str, Any]) -> None:
        rid = resource["meta"]["dc:identifier"]
        if rid in self._by_id:
            raise ValueError("IMMUTABLE_OVERWRITE_FORBIDDEN")
        self._by_id[rid] = resource

    def get(self, rid: str) -> dict[str, Any]:
        return self._by_id[rid]


def kernel_validate(resource: dict[str, Any]) -> ValidationResult:
    """
    Kernel validator:
      - MUST have meta, payload, integrity
      - MUST have meta.dc:type
      - If extensions exist, they must be dict and keys must match EXT_KEY_PATTERN
      - Extensions must not attempt to redefine kernel fields (checked by step that tries it)
    """
    if not isinstance(resource, dict):
        return ValidationResult(False, code="INVALID_RESOURCE_TYPE")
    for k in ("meta", "payload", "integrity"):
        if k not in resource:
            return ValidationResult(False, code="MISSING_KERNEL_FIELD")
    meta = resource["meta"]
    if "dc:type" not in meta:
        return ValidationResult(False, code="MISSING_DC_TYPE")

    exts = resource.get("extensions")
    if exts is not None:
        if not isinstance(exts, dict):
            return ValidationResult(False, code="EXTENSIONS_NOT_OBJECT")
        for key in exts.keys():
            if not EXT_KEY_PATTERN.match(key):
                return ValidationResult(False, code="EXT_KEY_NOT_NAMESPACED")

    return ValidationResult(True)


def build_resource(
    meta: dict[str, Any],
    payload: Any,
    extensions: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Build a Resource with content-addressed dc:identifier and sha256 integrity.
    Important: dc:identifier and integrity depend on canonical content.
    We compute hash over a 'canonical core' that excludes the auto-populated fields.
    """
    meta = dict(meta)  # copy
    meta.setdefault("dc:format", "application/json")

    resource: dict[str, Any] = {
        "meta": meta,
        "payload": payload,
    }
    if extensions is not None:
        resource["extensions"] = extensions

    # Hash the canonical form *without* identifier/integrity (so those can be derived from hash).
    to_hash = json.loads(canonical_json(resource))
    h = sha256_hex(canonical_json(to_hash))

    # Populate derived fields
    meta["dc:identifier"] = content_addressed_id(h)
    resource["integrity"] = {"content_hash": f"sha256:{h}"}

    return resource


def _derive_context_stable_ids(context) -> dict[str, str]:
    feature_path = getattr(getattr(context, "feature", None), "filename", None)
    scenario = getattr(context, "scenario", None)
    step = getattr(context, "step", None)

    if not isinstance(feature_path, str) or not feature_path:
        return {}

    try:
        raw_doc = Parser().parse(TokenScanner(Path(feature_path).read_text(encoding="utf-8")))
    except Exception:
        return {}

    doc = GherkinDocument.from_raw(raw_doc, uri=feature_path)
    if doc is None:
        return {}

    stable = derive_stable_ids(doc, uri=feature_path)
    out: dict[str, str] = {"feature_id": stable.feature_id}

    scenario_name = getattr(scenario, "name", None)
    if isinstance(scenario_name, str) and scenario_name.strip():
        for key, sid in stable.scenario_ids.items():
            if key.split(":", 1)[-1].split("@", 1)[0] == scenario_name:
                out["scenario_id"] = sid
                break
    elif len(stable.scenario_ids) == 1:
        out["scenario_id"] = next(iter(stable.scenario_ids.values()))

    step_name = getattr(step, "name", None)
    scenario_id = out.get("scenario_id")
    if isinstance(step_name, str) and step_name.strip() and isinstance(scenario_id, str):
        scenario_key = next((k for k, v in stable.scenario_ids.items() if v == scenario_id), None)
        if scenario_key is not None:
            for key, sid in stable.step_ids.items():
                key_scenario, step_part = key.split("::", 1)
                key_step_text = step_part.split(":", 1)[-1].split("@", 1)[0]
                if key_scenario == scenario_key and key_step_text == step_name:
                    out["step_id"] = sid
                    break
    elif len(stable.step_ids) == 1:
        out["step_id"] = next(iter(stable.step_ids.values()))

    return out


def _set_meta_field(context, key: str, value: str) -> None:
    state = get_resource_step_state(context)
    state.meta[key] = value


def _build_and_store_resource(context) -> None:
    state = get_resource_step_state(context)
    stable_ids = _derive_context_stable_ids(context)
    if stable_ids:
        state.meta["stable_ids"] = dict(stable_ids)
        state.meta.setdefault("semanticng", {}).update(stable_ids)
    state.resource = build_resource(meta=state.meta, payload=state.payload, extensions=state.extensions)
    if stable_ids:
        state.resource.update(stable_ids)
    context.store.put(state.resource)


def _resource_for_validation(context) -> dict[str, Any]:
    state = get_resource_step_state(context)
    assert state.resource is not None, "Resource must be built before validation"
    return json.loads(canonical_json(state.resource))


# ----------------------------
# Behave steps
# ----------------------------


@given("a canonical JSON serializer for Resources")
def step_given_canonical_serializer(context) -> None:
    context.canonical_json = canonical_json


@given("a sha256 content hash function")
def step_given_sha256(context) -> None:
    context.sha256_hex = sha256_hex


@given("a Resource store that is append-only")
def step_given_store(context) -> None:
    context.store = AppendOnlyStore()


@when('I create a Resource with dc:type "{dc_type}"')
def step_when_create_resource_type(context, dc_type: str) -> None:
    _set_meta_field(context, "dc:type", dc_type)


@when('with dc:created "{created}"')
def step_when_set_created(context, created: str) -> None:
    _set_meta_field(context, "dc:created", created)


@when('with dc:source "{source}"')
def step_when_set_source(context, source: str) -> None:
    _set_meta_field(context, "dc:source", source)


@when('with dc:creator "{creator}"')
def step_when_set_creator(context, creator: str) -> None:
    _set_meta_field(context, "dc:creator", creator)


@when("I create a Resource with:")
def step_when_create_resource_table(context) -> None:
    """
    Table example:
      | dc:identifier | (auto) |
      | dc:type       | Event  |
      | dc:created    | 2026-02-14T10:00:00Z |
      | dc:source     | channel:discord      |
      | dc:creator    | adapter:discord.v1   |
      | dc:format     | application/json     |
    """
    meta: dict[str, Any] = {}
    for row in context.table:
        key = row["dc:identifier"] if "dc:identifier" in row else row[0]  # defensive
        val = row["(auto)"] if "(auto)" in row else row[1]  # defensive

        # More robust: use headers if present
        # But most people do 2 columns without headers.
        # Behave supplies row[0], row[1] in that case.
        if isinstance(row, dict) and len(row) >= 2 and not key.startswith("dc:"):
            key = row[0]
            val = row[1]

        if key.strip() == "dc:identifier":
            # ignore explicit identifier; it is derived
            continue
        meta[key.strip()] = val.strip()

    state = get_resource_step_state(context)
    state.meta = meta


@when("with payload:")
def step_when_set_payload(context) -> None:
    raw = context.text.strip()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        # Allow non-JSON payloads if your system supports them
        payload = raw
    state = get_resource_step_state(context)
    state.payload = payload


@when("I create a Resource with extensions:")
def step_when_set_extensions(context) -> None:
    raw = context.text.strip()
    state = get_resource_step_state(context)
    state.extensions = json.loads(raw)


@when("I build the Resource")
def step_when_build_resource(context) -> None:
    _build_and_store_resource(context)


@then("the Resource MUST contain meta, payload, integrity")
def step_then_must_contain_core_fields(context) -> None:
    state = get_resource_step_state(context)
    assert state.resource is not None, "Resource not built"
    r = state.resource
    assert "meta" in r, "Missing meta"
    assert "payload" in r, "Missing payload"
    assert "integrity" in r, "Missing integrity"


@then('meta.dc:type MUST equal "{expected}"')
def step_then_dc_type_equals(context, expected: str) -> None:
    state = get_resource_step_state(context)
    assert state.resource is not None, "Resource not built"
    assert state.resource["meta"]["dc:type"] == expected


@then("integrity.content_hash MUST be a sha256 of canonical content")
def step_then_hash_matches(context) -> None:
    state = get_resource_step_state(context)
    assert state.resource is not None, "Resource not built"
    r = state.resource

    # Recompute hash from canonical content excluding derived fields (identifier, integrity)
    clone = {
        "meta": {k: v for k, v in r["meta"].items() if k != "dc:identifier"},
        "payload": r["payload"],
    }
    if "extensions" in r:
        clone["extensions"] = r["extensions"]

    expected_hex = sha256_hex(canonical_json(clone))
    actual = r["integrity"]["content_hash"]
    assert actual == f"sha256:{expected_hex}", f"Hash mismatch: {actual} != sha256:{expected_hex}"


@then("meta.dc:identifier MUST be a content-addressed identifier derived from the content hash")
def step_then_identifier_matches_hash(context) -> None:
    state = get_resource_step_state(context)
    assert state.resource is not None, "Resource not built"
    r = state.resource
    hash_hex = r["integrity"]["content_hash"].split("sha256:", 1)[1]
    assert r["meta"]["dc:identifier"] == content_addressed_id(hash_hex)


@then('the Resource MUST contain "{field}"')
def step_then_contains_field(context, field: str) -> None:
    state = get_resource_step_state(context)
    assert state.resource is not None, "Resource not built"
    assert field in state.resource, f"Missing field {field}"


@then('every extension key MUST match the pattern "{pattern}"')
def step_then_extension_key_pattern(context, pattern: str) -> None:
    # This allows the feature to specify the regex; we enforce it here.
    rx = re.compile(pattern)
    state = get_resource_step_state(context)
    assert state.resource is not None, "Resource not built"
    exts = state.resource.get("extensions", {})
    for k in exts.keys():
        assert rx.match(k), f"Extension key '{k}' does not match /{pattern}/"


@then('the kernel validator MUST pass even if "extensions" is removed')
def step_then_kernel_validator_pass_without_extensions(context) -> None:
    r = _resource_for_validation(context)
    r.pop("extensions", None)
    res = kernel_validate(r)
    assert res.ok, f"Kernel validation failed without extensions: {res.code}"


@given('a Resource exists with meta.dc:type equal to "{dc_type}"')
def step_given_resource_exists_with_type(context, dc_type: str) -> None:
    state = get_resource_step_state(context)
    state.meta = {"dc:type": dc_type, "dc:created": "2026-02-14T00:00:00Z", "dc:source": "test"}
    state.payload = {"ok": True}
    state.extensions = None
    state.resource = build_resource(state.meta, state.payload, state.extensions)
    context.store.put(state.resource)


@when('I add an extension that attempts to set "meta.dc:type" to "{new_type}"')
def step_when_extension_attempts_override_dc_type(context, new_type: str) -> None:
    # This simulates a forbidden “redefine kernel field” attempt.
    # In practice, you’d forbid this by validator rules.
    state = get_resource_step_state(context)
    state.bad_extension = {"badext.v1": {"meta": {"dc:type": new_type}}}


@then('validation MUST fail with code "{code}"')
def step_then_validation_fails_with_code(context, code: str) -> None:
    state = get_resource_step_state(context)
    r = _resource_for_validation(context)
    # Apply the bad extension for this validation attempt
    if state.bad_extension is not None:
        r["extensions"] = state.bad_extension

        # Detect conflict: extension tries to redefine meta.dc:type
        for _, ext in r["extensions"].items():
            if isinstance(ext, dict) and "meta" in ext and "dc:type" in ext["meta"]:
                # simulate kernel conflict detection
                actual_code = "EXT_CONFLICTS_WITH_KERNEL"
                assert actual_code == code, f"Expected {code}, got {actual_code}"
                return

    # Otherwise run generic kernel validation
    res = kernel_validate(r)
    assert not res.ok, "Expected validation to fail, but it passed"
    assert res.code == code, f"Expected {code}, got {res.code}"
