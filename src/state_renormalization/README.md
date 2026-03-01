# State Renormalization Module

## Active implementation directive

This module is the current orchestration and adapter shell around evolving core semantics.
Refactor work must follow `src/core/REFACTORING_METAPLAN.md` and preserve clean boundaries.

## Local boundary rules

`src/state_renormalization/` may coordinate execution and infrastructure integration, but must not absorb deterministic domain logic that belongs in `src/core/`.

Contributors must:

- keep I/O and integration concerns in adapters under `src/state_renormalization/adapters/`,
- define and consume explicit contracts when calling core logic,
- isolate nondeterministic sources behind adapter/port boundaries,
- migrate legacy behaviors slice-by-slice toward core ownership.

## How to contribute during refactor

1. Identify one capability slice currently implemented here.
2. Define or refine the contract used by that slice.
3. Add parity/invariant coverage for existing behavior.
4. Move deterministic domain logic into `src/core/` behind a facade seam.
5. Keep only orchestration and adapter wiring in this module.
6. Remove legacy path once parity and adoption are confirmed.

## Non-goals for this module

- introducing new hidden side effects in domain paths,
- broad rewrites without seam contracts and parity checks,
- bypassing adapter boundaries to call infrastructure directly from core logic.
