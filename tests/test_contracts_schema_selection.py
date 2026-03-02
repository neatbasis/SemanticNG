from __future__ import annotations

from state_renormalization.contracts import SchemaHit, SchemaSelection


def test_schema_selection_model_dump_shape_is_deterministic_with_optional_fields() -> None:
    selection = SchemaSelection(
        schemas=[
            SchemaHit(
                name="actionable_intent",
                score=0.91,
                schema_id="schema:actionable_intent",
                source="selector:default",
            )
        ],
        ambiguities=[],
        notes=None,
    )

    assert selection.model_dump(mode="json") == {
        "schemas": [
            {
                "name": "actionable_intent",
                "score": 0.91,
                "about": None,
                "schema_id": "schema:actionable_intent",
                "source": "selector:default",
            }
        ],
        "ambiguities": [],
        "notes": None,
    }


def test_schema_hit_accepts_legacy_payload_without_new_optional_fields() -> None:
    payload = {"name": "legacy.schema", "score": 0.4, "about": None}

    parsed = SchemaHit.model_validate(payload)

    assert parsed.schema_id is None
    assert parsed.source is None
    assert parsed.model_dump(mode="json") == {
        "name": "legacy.schema",
        "score": 0.4,
        "about": None,
        "schema_id": None,
        "source": None,
    }
