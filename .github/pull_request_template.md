## Summary

- Describe what changed and why.

## Validation

- [ ] I ran the required tests for this change.
- [ ] If this PR touches `src/state_renormalization/`, I ran all mandatory in-progress milestone commands from `docs/dod_manifest.json`.
- [ ] For every capability status transition in `docs/dod_manifest.json`, this PR description includes all exact milestone `pytest` command(s) from the manifest in the required `Milestone pytest commands + CI evidence links` format below.

## Capability updates (if applicable)

- Capability ID(s):
- Status transition(s):

## Milestone pytest commands + CI evidence links (required for capability status transitions)

For each transitioned capability, copy each `pytest` command exactly as written in `docs/dod_manifest.json` and use deterministic two-line pairs:

```text
<exact command string>
Evidence: https://...
```

The evidence line must be immediately after the command and must contain exactly one URL on that line.

Example layout:

```text
pytest tests/test_example.py tests/test_other.py
Evidence: https://github.com/<org>/<repo>/actions/runs/123456789/job/987654321#step:5:18
```
