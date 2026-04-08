**GAP TAXONOMY REFERENCE**

neatbasis Ontology Gap Detection Framework

*Version 1.0 · Reference Document*

**1. Purpose**

This document defines the canonical taxonomy of ontology gap types used
across the neatbasis portfolio. Every gap finding recorded in the gap
ledger must be classified against this taxonomy. The taxonomy is the
primary instrument for ensuring gap findings are actionable rather than
generic.

**2. Core Definition**

An **ontology gap** is a missing, conflated, weakly constrained, weakly
aligned, or operationally inadequate representational element whose
absence reduces the system's ability to support intended interpretation,
reasoning, validation, explanation, interoperability, or decision
support.

**3. Taxonomy Table**

|        |                                |                                                                                                                    |                                                                                                |                                                                                               |
|--------|--------------------------------|--------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------|
| **ID** | **Gap Type**                   | **Definition**                                                                                                     | **Signal / Symptom**                                                                           | **Typical Remediation**                                                                       |
| **A**  | **Vocabulary Gap**             | A concept, relation, qualifier, or class is simply absent.                                                         | Recurring need for an unnamed concept; use of free text or ad hoc predicates.                  | Add vocabulary (class, property, or pattern element).                                         |
| **B**  | **Granularity Gap**            | Ontology has something in the right area but not at the right resolution.                                          | One class or property accumulates multiple subtly different meanings.                          | Split class or property; add sub-types or qualified relations.                                |
| **C**  | **Boundary Gap**               | A concept belongs at the boundary between ontologies but the boundary is unclear or unmodeled.                     | Duplicate modeling across modules; recurring ambiguity about "which ontology should own this". | Add explicit boundary rule to authority draft; add owl:equivalentClass or rdfs:seeAlso links. |
| **D**  | **Alignment Gap**              | Two ontologies should interoperate but the mapping is absent, weak, or semantically risky.                         | Equivalent things live in isolated silos; bridging queries require ad hoc application logic.   | Add SKOS mappings or OWL alignment axioms; update boundary matrix.                            |
| **E**  | **Constraint Gap**             | Something invalid or pathological can be expressed without formal friction.                                        | Pathological instances pass silently; validation catches too little.                           | Add SHACL shapes for required properties, cardinality, or conditional patterns.               |
| **F**  | **Disambiguation Gap**         | The ontology permits conflation between things that should be distinguishable.                                     | Multiple interpretations fit equally well; downstream systems make inconsistent assumptions.   | Add owl:disjointWith axioms; add role-contextualizing relations.                              |
| **G**  | **Epistemic Gap**              | The ontology cannot represent knowledge state, uncertainty, verification status, conflict, or confidence.          | Absence is misread as falsity; confidence/provenance handled only informally.                  | Add epistemic state vocabulary; add claim-state model (PostingEpistemics).                    |
| **H**  | **Provenance Gap**             | Facts cannot be traced to source artifacts, extraction processes, or interpretation steps.                         | Assertions exist without prov:wasDerivedFrom or prov:wasGeneratedBy.                           | Add provenance chain pattern; enforce via SHACL.                                              |
| **I**  | **Temporal Gap**               | Facts lack temporal qualification, lifecycle semantics, or interval reasoning support.                             | Impossible to distinguish current from historical truth; expired facts contaminate queries.    | Add OWL-Time constructs; apply portfolio time-qualification rule.                             |
| **J**  | **Spatial Gap**                | Entities have locations as values but not as spatially reason-able structures.                                     | Location can be displayed but not reasoned over.                                               | Add GeoSPARQL feature/geometry typing; enforce spatial upgrade path.                          |
| **K**  | **Spatiotemporal Extent Gap**  | The ontology cannot represent an entity's state, identity, validity, and relations across time and space together. | Separate time and location fields cannot be jointly used for reasoning.                        | Add joint spatiotemporal pattern; align GeoSPARQL and OWL-Time usage.                         |
| **L**  | **Closure Gap**                | The ontology is not closed under the operations required by intended reasoning.                                    | Ontology supports representation but not the transformations needed for inference.             | Add composition rules; extend reasoning profile; add SHACL derivation constraints.            |
| **M**  | **Pattern Gap**                | Vocabulary exists but a recurring modeling pattern is absent.                                                      | Each module or team invents its own local workaround.                                          | Define and document a reusable pattern; add to pattern library.                               |
| **N**  | **Instance Accommodation Gap** | Real-world data contains fields or distinctions that do not fit the ontology cleanly.                              | Data ends up in string blobs or generic comment fields.                                        | Add vocabulary or pattern identified by real-data instantiation pass.                         |
| **O**  | **Import Interaction Gap**     | Imported ontologies interact in ways that create unsound or unintended consequences.                               | Reasoner behavior changes drastically after adding a new import.                               | Run import conservativity test; isolate or remap conflicting axioms.                          |
| **P**  | **Decision-Risk Gap**          | A missing distinction materially increases the risk of harmful or misleading decisions.                            | Downstream decisions appear more justified than they are.                                      | Prioritize based on operational harm score; address before deployment.                        |

**4. Gap Severity Dimensions**

Every gap finding must be scored on the following dimensions when
recorded in the gap ledger.

|                        |                                           |                                                                             |
|------------------------|-------------------------------------------|-----------------------------------------------------------------------------|
| **Dimension**          | **Scale**                                 | **Notes**                                                                   |
| **Operational Impact** | 0 (negligible) – 4 (severe failure risk)  | How much does this gap degrade real system competence?                      |
| **Frequency**          | rare / occasional / common / pervasive    | How often does the gap manifest in real data or queries?                    |
| **Scope**              | local / cross-module / portfolio-wide     | How many ontology modules or systems are affected?                          |
| **Recoverability**     | easy / partial / hard / redesign required | Can the system recover with application logic or is ontology change needed? |
| **Epistemic Risk**     | none / low / medium / high                | Does this gap create false confidence, ambiguity, or hidden uncertainty?    |
| **Decision Risk**      | none / low / medium / high                | Could this gap materially worsen a decision?                                |

**5. Remediation Pattern Catalogue**

Map each gap finding to the lowest-cost adequate remediation pattern
before escalating to ontology redesign.

- Add vocabulary (class, property, or qualifier)

- Add alignment (SKOS mapping or OWL equivalence axiom)

- Add SHACL shape (constraint or closed-world validation)

- Add temporal qualification pattern

- Add provenance chain pattern

- Split or refactor class or property

- Add epistemic state model (local extension)

- Define reusable modeling pattern for pattern library

- Add local ontology extension module (gap-ledger-motivated)

- Refactor upper/mid-level alignment family

- Add import isolation or bridge module

**6. Classification Rules**

- Classify before scoring. Gap type determines which test family
  surfaces it and which remediation applies.

- A gap may have more than one type if it spans multiple failure modes.
  Record the primary type and note secondary types.

- Distinguish ontology gaps from data gaps, extraction gaps, validation
  gaps, query gaps, and governance gaps. These require different
  remediation.

- Do not assign Decision-Risk (P) as the sole type. It should be
  co-assigned with the structural gap type that enables the risk.
