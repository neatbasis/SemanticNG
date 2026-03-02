# Editor setup (VS Code + CLI fallback)

## VS Code (recommended)

1. Install the **Ruff** extension (`charliermarsh.ruff`).
2. Install the **Mypy Type Checker** extension (`ms-python.mypy-type-checker`).
3. Open this repository in VS Code; repo defaults are committed in `.vscode/settings.json`.

These defaults enable Ruff diagnostics + Ruff format-on-save and workspace mypy diagnostics with:

```bash
mypy --config-file=pyproject.toml src/state_renormalization src/core
```

## Verify in the first 5 minutes

After opening VS Code, create a temporary type error in a Python file under `src/core/` and confirm:

- Ruff highlights lint/import issues.
- Mypy reports a type error in the Problems panel.
- Saving the file runs Ruff formatting.

You can also verify with canonical CLI commands:

```bash
ruff check src tests
ruff format --check src tests
mypy --config-file=pyproject.toml src/state_renormalization src/core
```

## Fallback CLI loop (editor-agnostic)

If editor diagnostics are unavailable, run this loop while editing:

```bash
ruff check src tests && ruff format --check src tests && mypy --config-file=pyproject.toml src/state_renormalization src/core
```

For full CI-parity typing beyond Tier 1 strict scope:

```bash
mypy --config-file=pyproject.toml src tests
```
