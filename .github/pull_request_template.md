## Summary

- Describe the change.

## Testing

- List tests/checks run for this PR.

## Milestone pytest commands and CI evidence (required for status transitions)

For every milestone status transition in this PR, include each exact `pytest` command on one line and one adjacent `https://...` evidence line immediately below it.

```text
pytest tests/milestones/test_alpha.py -k gate
https://github.com/<org>/<repo>/actions/runs/123456789

pytest tests/milestones/test_beta.py -k readiness
https://github.com/<org>/<repo>/actions/runs/987654321
```

- Do not summarize commands; copy/paste the exact command line.
- Do not group multiple commands under one link.
- Ensure each command has its own adjacent `https://...` CI evidence line.
