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

For each transitioned capability, copy each `pytest` command exactly as written in `docs/dod_manifest.json` and include CI evidence nearby using this pattern:

```text
<exact command string>
Evidence: https://...
```

`Evidence: https://...` must appear on line 2 or within the next 3 lines after each command.

Example layout:

```text
pytest tests/test_example.py tests/test_other.py
Evidence: https://github.com/<org>/<repo>/actions/runs/123456789/job/987654321#step:5:18
```
