# Directive records

Decision/directive records live in `docs/directives/` as JSON files.

## Naming convention

- Canonical file format: `DR-YYYY-NNN-title.json`
  - `YYYY` is the year.
  - `NNN` is a zero-padded sequence.
  - `title` is a short kebab-case slug.
- Optional generated companion markdown may be emitted next to a JSON record using the same base name, e.g. `DR-2026-001-example.md`.

All JSON records in this folder are validated by `scripts/ci/validate_decision_records.py`.
