**PROCESS EXECUTION GUIDE**

Ontology Operationalization Process — neatbasis Portfolio

*Version 1.0 · Governing Process Document*

**1. Purpose**

This document defines the phased process for operationalizing the
neatbasis ontology portfolio. It is the governing instrument that
sequences the other six documents in this set into an executable
program.

The process is evidence-first and remediation-last. No TTL file is
modified before the instantiation pass produces confirmed gap evidence.
No gap is closed without a test confirming closure.

**2. Document Set**

|        |                                             |                                                             |
|--------|---------------------------------------------|-------------------------------------------------------------|
| **\#** | **Document**                                | **Role in Process**                                         |
| **1**  | **Ontology Portfolio Catalogue**            | Primary reference for all authority and layer decisions.    |
| **2**  | **Gap Taxonomy Reference**                  | Classification instrument for all gap findings.             |
| **3**  | **Test Family Matrix**                      | Test selection instrument — maps gap types to test methods. |
| **4**  | **Posting Cluster Authority Draft v0**      | Boundary control document for the posting domain.           |
| **5**  | **Posting Annotation Worksheet**            | Instantiation instrument for real-data testing.             |
| **6**  | **Gap Ledger Schema**                       | Governance instrument for all gap findings and resolutions. |
| **7**  | **Process Execution Guide (this document)** | Governing process — sequences all other documents.          |

**3. Governing Principles**

|                                              |                                                                                                                                                                                                    |
|----------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Principle**                                | **Statement**                                                                                                                                                                                      |
| **Evidence before formalism**                | No ontology artifact is created without a gap ledger entry motivating it. No gap is assumed without evidence from at least one test family.                                                        |
| **Pattern before vocabulary**                | Before adding a new class or property, check whether a reusable modeling pattern can accommodate the distinction. Vocabulary additions are more expensive than pattern additions.                  |
| **Provenance non-negotiable**                | Every extracted or inferred fact must carry a provenance chain. This is enforced by SHACL, not by convention.                                                                                      |
| **Time qualification mandatory**             | Every fact that can change over time must be time-qualified. The portfolio rule list (Document 4, Section 7) defines which facts are mandatory.                                                    |
| **Layered authority preserved**              | No ontology module may claim authority over distinctions owned by another module. The boundary matrix is the authority record.                                                                     |
| **Import conservativity after every change** | Every import or alignment addition must be followed by a conservativity test before the change is merged.                                                                                          |
| **Lean: no gap left informal**               | Every gap detected enters the ledger within 48 hours. Informal notes are not gaps — they are pre-gap observations that must be promoted or discarded.                                              |
| **Acceleration over elegance**               | The goal is a system that learns and corrects itself. A working gap-detection process that produces evidence quickly is more valuable than a theoretically complete ontology that is never tested. |

**4. Phased Process**

**Phase 1: Portfolio Inventory**

**Goal:** Make the implicit portfolio architecture explicit and
queryable.

**Inputs**

- Ontology Portfolio Catalogue (Document 1)

- Posting Cluster Authority Draft (Document 4)

**Outputs**

- Populated boundary matrix

- Initial authority and connection rules

- Identified pressure points for Phase 2

**Active Test Families**

- Role Boundary Matrix Testing

**Execution Rules**

1.  Complete the per-module template (section 14 of the reference
    framework) before running any SPARQL query or SHACL shape.

2.  Record boundary ambiguities and likely gap types as hypotheses — not
    confirmed gaps yet.

3.  Use the Posting Cluster Authority Draft to focus inventory attention
    on the highest-pressure cluster.

**Phase Gate**

**Gate condition:** *Every ontology in scope has a completed inventory
record with layer, authority, non-authority, and likely boundary
ambiguities documented.*

**Phase 2: Real-Data Instantiation and Competency Testing**

**Goal:** Surface gaps from real data and intended queries before
touching TTL files.

**Inputs**

- Posting Annotation Worksheet (Document 5)

- 5–10 real Finnish job postings (mix: direct employer, named-principal
  agency, hidden-principal agency)

- Competency question suite (to be authored)

**Outputs**

- Completed annotation worksheets

- Initial gap ledger entries (Document 6)

- Confirmed or refuted hypotheses H1–H7

- PostingEpistemics.ttl motivation list

**Active Test Families**

- Real-Data Instantiation Testing

- Competency Question Testing

- Provenance Completeness Testing

**Execution Rules**

4.  Do not modify any TTL file during this phase.

5.  For each posting field, record both the raw value and the gap
    outcome using the worksheet categories.

6.  A field that is awkward but has a home is not a gap. A field with no
    clean home is a gap.

7.  Record provenance failures (fields that exist without a provenance
    path) as Type H gaps immediately.

**Phase Gate**

**Gate condition:** *At least 5 postings annotated; at least one gap
ledger entry per confirmed hypothesis; all entries classified by gap
type.*

**Phase 3: Formal Structure and Closure Testing**

**Goal:** Verify logical structure, constraint coverage, and closure
properties.

**Inputs**

- Gap ledger from Phase 2

- Current TTL files

- SHACL profile drafts

**Outputs**

- OWL reasoner report

- SHACL validation report

- Temporal and spatial closure test results

- Import conservativity report

- Additional gap ledger entries

**Active Test Families**

- Logical Consistency and Disjointness Testing

- SHACL / Closed-World Constraint Testing

- Temporal Closure Testing

- Spatial Representation and Closure Testing

- Spatiotemporal Adequacy Testing

- Import Conservativity Testing

- Identity Resolution Stress Testing

- Epistemic Stress Testing

**Execution Rules**

8.  Run import conservativity test after every new import or alignment
    axiom addition.

9.  Write SHACL shapes for mandatory provenance and temporal
    qualification before testing instances.

10. Negative example testing must precede any SHACL shape being marked
    "sufficient".

11. Spatial testing is not required until GeoSPARQL integration is
    underway.

**Phase Gate**

**Gate condition:** *No unsatisfiable classes; no unintended
subclassing; mandatory SHACL shapes pass on synthetic clean data;
temporal closure test passes for posting validity interval.*

**Phase 4: Risk, Abduction, and Pattern Review**

**Goal:** Find operationally consequential gaps and missing explanatory
constructs.

**Inputs**

- Gap ledger from Phase 3

- Domain expert availability

- Explanation traces from Phase 2–3 queries

**Outputs**

- Decision-risk assessment per open gap

- Abductive gap findings

- Pattern library additions

- Prioritized remediation backlog

**Active Test Families**

- Decision-Risk Testing

- Abductive Gap Testing

- Pattern Conformance Testing

**Execution Rules**

12. Decision-risk assessment requires domain judgment, not only ontology
    engineer judgment.

13. Abductive review: for every repeated explanation failure, ask what
    concept or relation is missing.

14. Pattern library additions require a concrete reusable pattern
    document, not just a note.

15. Pattern gaps (Type M) discovered here must be back-linked to the
    Phase 2 instances that first required the pattern.

**Phase Gate**

**Gate condition:** *Every open gap has a decision-risk score; no gap
with decision-risk "high" and operational impact ≥ 3 is unaddressed
before a deployment milestone.*

**Phase 5: Remediation and Regression**

**Goal:** Close confirmed gaps with the minimum adequate remediation and
verify closure.

**Inputs**

- Prioritized gap backlog

- Remediation pattern library

- PostingEpistemics.ttl skeleton (from Phase 2 outputs)

**Outputs**

- Updated TTL files

- PostingEpistemics.ttl v0.1+

- SHACL profile updates

- Gap ledger closures with resolution evidence

**Active Test Families**

- All relevant Phase 2–4 tests re-run post-remediation

- Import Conservativity Testing (mandatory after every change)

**Execution Rules**

16. No class or property is added without a gap ledger entry motivating
    it.

17. No gap is marked resolved without a cited test result.

18. After every TTL change: run reasoner, run relevant SHACL shapes, run
    import conservativity test.

19. Remediation that introduces new gaps (detected by import
    conservativity) must be redesigned before merging.

20. PostingEpistemics.ttl v0 skeleton must not exceed what the
    instantiation pass evidence supports.

**Phase Gate**

**Gate condition:** *Every remediation has: a gap ledger entry, a test
confirming closure, and an import conservativity check.*

**5. Decision Gates**

The following decisions must be explicitly made and recorded before
proceeding. They are not optional checkpoints.

|                                       |                                                                                                                                                    |
|---------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------|
| **Gate**                              | **Condition**                                                                                                                                      |
| **Before Phase 2**                    | Portfolio inventory complete; authority draft approved; annotation worksheet ready.                                                                |
| **Before first TTL edit**             | At least 5 postings annotated; at least one gap ledger entry per confirmed hypothesis.                                                             |
| **Before Phase 3 formal tests**       | Gap ledger from Phase 2 reviewed; SHACL shapes drafted for mandatory provenance and temporal qualification.                                        |
| **Before PostingEpistemics.ttl v0.1** | Instantiation pass complete; gap ledger contains specific motivated entries for every class and property to be added.                              |
| **Before any deployment milestone**   | No gap with decision-risk "high" and operational impact ≥ 3 is unresolved; import conservativity passes; mandatory SHACL shapes pass on real data. |
| **Mid-level alignment fork**          | Before MissionContext.ttl advances beyond skeleton: BFO/CCO vs UFO/gUFO decision recorded in catalogue and in MissionContext.ttl header.           |
| **Before architecture refactor planning** | Project concept-binding outputs are complete and current: (1) capability identifier relationship clarified in `docs/ontology/01-ontology-portfolio-catalogue.md`; (2) runtime concept taxonomy present in `docs/system_contract_map.md`; (3) purpose-stack linkage present in `docs/system_contract_map.md`; (4) step-layer authority boundary present in `docs/system_contract_map.md`; and linked gap-tracking evidence exists in the authoritative gap ledger (`gaps/ledger.yaml` or `gaps/LEDGER.md`). If any required output is missing or stale, this gate is fail-closed and refactor planning does not proceed. |

**6. Artifact Dependency Map**

The sequence in which artifacts must be produced. No artifact may be
produced before its dependencies exist.

21. Portfolio inventory (from Document 1 template) → boundary matrix
    draft

22. Boundary matrix + authority draft → annotation worksheet readiness

23. Annotation worksheets (≥5) → gap ledger entries →
    PostingEpistemics.ttl motivation list

24. Gap ledger entries → PostingEpistemics.ttl v0 skeleton

25. PostingEpistemics.ttl v0 + SHACL shapes → Phase 3 formal testing

26. Phase 3 results → Phase 4 risk and abduction review

27. Phase 4 prioritized backlog → Phase 5 remediation

28. Each remediation → import conservativity test → gap closure with
    evidence

**7. Deliverables This Process Produces**

|                                       |                       |                                              |
|---------------------------------------|-----------------------|----------------------------------------------|
| **Deliverable**                       | **Produced in Phase** | **Notes**                                    |
| **Populated boundary matrix**         | 1                     | Living document; updated throughout.         |
| **Annotated posting worksheets**      | 2                     | Minimum 5; archive permanently.              |
| **Gap ledger (initial)**              | 2                     | YAML or RDF; version-controlled.             |
| **PostingEpistemics.ttl v0 skeleton** | 2→3                   | Evidence-motivated only.                     |
| **SHACL profile (provenance + time)** | 3                     | Mandatory shapes first.                      |
| **OWL reasoner report**               | 3                     | Run on each import change.                   |
| **Temporal closure test suite**       | 3                     | SPARQL queries for interval operations.      |
| **Spatial closure test suite**        | 3                     | When GeoSPARQL integration is active.        |
| **Prioritized remediation backlog**   | 4                     | Scored gap ledger, sorted by priority score. |
| **Pattern library**                   | 4→5                   | Reusable patterns in portfolio docs.         |
| **Gap ledger closures with evidence** | 5                     | Permanent record of resolved gaps.           |
| **MissionContext.ttl skeleton**       | Post-Phase 5          | After mid-level alignment fork decision.     |

**8. Immediate Next Action**

The immediate next action is: **annotate one real Finnish posting
end-to-end against Document 4 using Document 5 before touching any TTL
file.**

This single action will produce more useful signal than any amount of
additional taxonomy work. The gap ledger entry that results from the
first fully annotated posting is the empirical foundation of the entire
remediation program.
