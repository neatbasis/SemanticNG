**TEST FAMILY MATRIX**

neatbasis Ontology Gap Detection Framework

*Version 1.0 · Reference Document*

**1. Purpose**

This document maps the sixteen gap types from the Gap Taxonomy Reference
to the sixteen test families available for detecting them. Use it to
select the right tests for a given gap hypothesis and to ensure
portfolio coverage across all gap types.

**2. Legend**

● Primary: this test family is the primary instrument for detecting this
gap type.

Blank: this test family does not reliably detect this gap type.

Gap type codes refer to the Gap Taxonomy Reference (Document 2). Test
families are executed in the phase order shown.

**3. Gap-Type Codes**

|            |             |                |           |            |                |                    |               |
|------------|-------------|----------------|-----------|------------|----------------|--------------------|---------------|
| **A**      | **B**       | **C**          | **D**     | **E**      | **F**          | **G**              | **H**         |
| Vocabulary | Granularity | Boundary       | Alignment | Constraint | Disambiguation | Epistemic          | Provenance    |
| **I**      | **J**       | **K**          | **L**     | **M**      | **N**          | **O**              | **P**         |
| Temporal   | Spatial     | Spatiotemporal | Closure   | Pattern    | Instance       | Import Interaction | Decision-Risk |

**4. Coverage Matrix**

Orientation: rows = test families, columns = gap types. Landscape
orientation aids readability; print at 90% scale if needed.

|                                              |       |       |       |       |       |       |       |       |       |       |       |       |       |       |       |       |                    |
|----------------------------------------------|-------|-------|-------|-------|-------|-------|-------|-------|-------|-------|-------|-------|-------|-------|-------|-------|--------------------|
| **Test Family**                              | **A** | **B** | **C** | **D** | **E** | **F** | **G** | **H** | **I** | **J** | **K** | **L** | **M** | **N** | **O** | **P** | **Phase**          |
| Competency Question Testing                  | **●** | **●** |       | **●** |       |       |       | **●** | **●** |       |       |       |       |       |       |       | Phase 2 — early    |
| Logical Consistency and Disjointness Testing |       |       | **●** |       | **●** | **●** |       |       |       |       |       |       |       |       | **●** |       | Phase 2            |
| SHACL / Closed-World Constraint Testing      |       |       |       |       | **●** |       |       | **●** | **●** |       |       |       | **●** | **●** |       |       | Phase 2–3          |
| Real-Data Instantiation Testing              | **●** | **●** | **●** |       |       |       |       | **●** | **●** |       |       |       |       | **●** |       |       | Phase 2 — priority |
| Negative Example / Pathology Testing         |       |       |       |       | **●** |       | **●** | **●** | **●** |       |       |       |       |       |       | **●** | Phase 3            |
| Provenance Completeness Testing              |       |       |       |       |       |       |       | **●** |       |       |       |       | **●** |       |       | **●** | Phase 2 ongoing    |
| Temporal Closure Testing                     |       |       |       |       |       | **●** |       |       | **●** |       |       | **●** |       |       |       |       | Phase 3            |
| Spatial Representation and Closure Testing   |       |       |       | **●** |       |       |       |       |       | **●** |       | **●** |       |       |       |       | Phase 3            |
| Spatiotemporal Adequacy Testing              |       |       |       |       |       |       |       |       | **●** | **●** | **●** | **●** |       |       |       |       | Phase 3            |
| Role Boundary Matrix Testing                 |       | **●** | **●** | **●** |       |       |       |       |       |       |       |       |       |       |       |       | Phase 1 ongoing    |
| Import Conservativity Testing                |       |       | **●** |       |       | **●** |       |       |       |       |       |       |       |       | **●** |       | Phase 2–3          |
| Epistemic Stress Testing                     |       |       |       |       |       |       | **●** | **●** |       |       |       |       |       |       |       | **●** | Phase 3            |
| Identity Resolution Stress Testing           |       |       |       |       |       | **●** | **●** | **●** |       |       |       |       | **●** |       |       |       | Phase 3            |
| Decision-Risk Testing                        |       |       |       |       |       |       | **●** | **●** | **●** |       |       |       |       |       |       | **●** | Phase 4            |
| Abductive Gap Testing                        | **●** | **●** |       |       |       |       | **●** |       |       |       |       |       | **●** |       |       |       | Phase 3–4          |
| Pattern Conformance Testing                  |       |       |       |       | **●** |       |       | **●** | **●** |       |       |       | **●** |       |       |       | Phase 3            |

**5. Tools and Execution Phases**

|                                              |                                                  |                     |
|----------------------------------------------|--------------------------------------------------|---------------------|
| **Test Family**                              | **Primary Tools**                                | **Execution Notes** |
| Competency Question Testing                  | SPARQL; competency question suite                | Phase 2 — early     |
| Logical Consistency and Disjointness Testing | HermiT / Pellet OWL reasoner                     | Phase 2             |
| SHACL / Closed-World Constraint Testing      | Jena SHACL; TopBraid                             | Phase 2–3           |
| Real-Data Instantiation Testing              | Manual annotation worksheet; SPARQL verification | Phase 2 — priority  |
| Negative Example / Pathology Testing         | Negative example suite; SPARQL; reasoner         | Phase 3             |
| Provenance Completeness Testing              | SPARQL audit queries                             | Phase 2 ongoing     |
| Temporal Closure Testing                     | SPARQL; OWL-Time profile tests                   | Phase 3             |
| Spatial Representation and Closure Testing   | GeoSPARQL query tests                            | Phase 3             |
| Spatiotemporal Adequacy Testing              | Joint SPARQL; spatial + temporal profile         | Phase 3             |
| Role Boundary Matrix Testing                 | Authority draft; boundary matrix; manual review  | Phase 1 ongoing     |
| Import Conservativity Testing                | OWL reasoner before/after comparison             | Phase 2–3           |
| Epistemic Stress Testing                     | Epistemic scenario suite; SPARQL                 | Phase 3             |
| Identity Resolution Stress Testing           | Duplicate-source test corpus; SPARQL             | Phase 3             |
| Decision-Risk Testing                        | Harm scenario analysis; domain expert review     | Phase 4             |
| Abductive Gap Testing                        | Explanation trace review; analyst judgment       | Phase 3–4           |
| Pattern Conformance Testing                  | SHACL; pattern registry; instance review         | Phase 3             |

**6. Execution Rules**

- Run tests in phase order: Phase 1 (portfolio inventory) → Phase 2
  (instantiation + competency) → Phase 3 (formal + closure) → Phase 4
  (risk and abduction).

- A gap hypothesis raised during Phase 1 must be confirmed by at least
  one Phase 2 or 3 test before being recorded as a confirmed gap.

- Every test run must be dated and its outcome recorded in the gap
  ledger.

- Import conservativity testing must be run after every new import or
  alignment addition, regardless of phase.

- Decision-risk testing requires domain expert participation, not only
  ontology engineer judgment.
