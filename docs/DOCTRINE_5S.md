# 5S Governance Doctrine

This document captures the repository's **5S doctrine text** as a normative governance baseline for day-to-day delivery decisions, quality reviews, and merge readiness.

## Normative baseline doctrine text

The 5S doctrine is applied as five operating commitments:

1. **Sort** — separate essential changes from incidental complexity; remove or quarantine unused paths, dead docs, and stale waivers.
2. **Set in order** — make boundaries explicit (ownership, contracts, invariants, and file-level sources of truth) so reviewers can locate decision evidence quickly.
3. **Shine** — keep quality signals clean and actionable by resolving failing checks, stale metadata, and ambiguous governance language before merge.
4. **Standardize** — encode repeatable expectations in versioned docs, machine-readable policies, and automated checks rather than ad hoc interpretation.
5. **Sustain** — preserve gains through continuous verification, periodic governance review, and explicit accountability for regressions.

## Scope and precedence

This doctrine **complements** existing governance documents and does not replace them.

- `docs/AXIOMS.md` remains the repository-level normative axiom set.
- Module-local axioms/invariants (for example under `src/core/` and `src/semanticng/`) remain authoritative within their module scopes.
- Where this doctrine and a more-specific invariant differ, the more-specific invariant/contract/test requirement takes precedence.
- This doctrine should be used as decision framing for quality/governance behavior, while executable constraints continue to be enforced through contracts, invariants, and CI gates.

## Practical usage in PRs

Use this doctrine as a review lens when preparing or evaluating changes:

- confirm unnecessary scope was removed (**Sort**),
- verify artifacts and ownership are discoverable (**Set in order**),
- ensure quality/governance checks are green and clearly interpreted (**Shine**),
- align updates with canonical templates and validators (**Standardize**),
- document follow-through actions for risk/waiver retirement (**Sustain**).
