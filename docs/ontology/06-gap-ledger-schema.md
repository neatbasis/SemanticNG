**GAP LEDGER SCHEMA**

neatbasis Ontology Gap Detection Framework

*Version 1.0 · Governance Document*

**1. Purpose**

The gap ledger is the central governance instrument for ontology quality
in the neatbasis portfolio. Every gap detected by any test family must
be entered here. The ledger drives remediation prioritization, tracks
resolution status, and prevents gaps from being informally forgotten or
silently re-introduced.

**2. Ledger Schema**

|                                   |               |                                                                                       |                                                                                                                    |               |
|-----------------------------------|---------------|---------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------|---------------|
| **Field**                         | **Type**      | **Description**                                                                       | **Example**                                                                                                        | **Required?** |
| **GAP-ID**                        | string        | Unique gap identifier. Format: GAP-YYYYMM-NNN                                         | GAP-202604-001                                                                                                     | **Required**  |
| **Title**                         | string        | Short descriptive title of the gap (≤ 80 chars)                                       | Missing hidden-principal claim-state model                                                                         | **Required**  |
| **Gap Type (primary)**            | enum A–P      | Primary gap type from the Gap Taxonomy Reference                                      | G (Epistemic Gap)                                                                                                  | **Required**  |
| **Gap Type (secondary)**          | enum A–P list | Secondary gap types if applicable                                                     | H, C                                                                                                               | Optional      |
| **Affected Module(s)**            | ontology list | Which ontology modules are affected                                                   | SARO, ORG, PostingEpistemics                                                                                       | **Required**  |
| **Observed Symptom**              | text          | What was actually observed: failed query, awkward placement, unresolvable field, etc. | "Principal employer" field from Finnish posting has no clean place in SARO or ORG when employer is unnamed.        | **Required**  |
| **Evidence Source**               | string        | How was the gap found: which test family, which posting ID, which query               | Real-data instantiation, Posting P003, Section B                                                                   | **Required**  |
| **Evidence Date**                 | date          | When the gap was first observed                                                       | 2026-04-10                                                                                                         | **Required**  |
| **Hypothesis Confirmed**          | boolean       | Whether the gap confirms a pre-stated hypothesis                                      | true — H1                                                                                                          | **Required**  |
| **Operational Impact**            | integer 0–4   | Impact on system competence                                                           | 3                                                                                                                  | **Required**  |
| **Frequency**                     | enum          | rare / occasional / common / pervasive                                                | pervasive                                                                                                          | **Required**  |
| **Scope**                         | enum          | local / cross-module / portfolio-wide                                                 | cross-module                                                                                                       | **Required**  |
| **Epistemic Risk**                | enum          | none / low / medium / high                                                            | high                                                                                                               | **Required**  |
| **Decision Risk**                 | enum          | none / low / medium / high                                                            | high                                                                                                               | **Required**  |
| **Recoverability**                | enum          | easy / partial / hard / redesign required                                             | partial                                                                                                            | **Required**  |
| **Proposed Remediation Type**     | enum          | See Gap Taxonomy Reference Section 5                                                  | Add local ontology extension module                                                                                | **Required**  |
| **Proposed Remediation Detail**   | text          | Specific classes, properties, patterns, or SHACL shapes to add                        | Add pe:HiddenPrincipalState as SKOS concept scheme; add pe:hiringPrincipalClaimStatus property to posting cluster. | **Required**  |
| **Target Module for Remediation** | string        | Which TTL file or module receives the fix                                             | PostingEpistemics.ttl                                                                                              | **Required**  |
| **Linked Test to Confirm Fix**    | string        | Which test family and specific query/shape will confirm the gap is closed             | SHACL shape pe-shape-001; competency question CQ-17                                                                | **Required**  |
| **Priority Score**                | computed      | Optional: sum of scored dimensions for backlog ordering                               | 14 / 20                                                                                                            | Optional      |
| **Status**                        | enum          | open / in-remediation / resolved / deferred / rejected                                | open                                                                                                               | **Required**  |
| **Resolved Date**                 | date          | Date the gap was confirmed closed by a passing test                                   |                                                                                                                    | Conditional   |
| **Resolution Evidence**           | string        | Test ID and run date that confirmed closure                                           |                                                                                                                    | Conditional   |
| **Notes**                         | text          | Additional context, related gaps, open questions                                      |                                                                                                                    | Optional      |
| **Owner**                         | string        | Responsible engineer or team                                                          | Sebastian                                                                                                          | **Required**  |

**3. Priority Scoring Model**

Optional priority score = sum of dimension scores below. Use to sort the
open backlog.

|                              |                                                                          |                |
|------------------------------|--------------------------------------------------------------------------|----------------|
| **Dimension**                | **Scale**                                                                | **Max Points** |
| **Operational Impact**       | 0 = negligible, 1 = low, 2 = moderate, 3 = major, 4 = severe             | **4**          |
| **Frequency**                | rare = 1, occasional = 2, common = 3, pervasive = 4                      | **4**          |
| **Scope**                    | local = 1, cross-module = 2, portfolio-wide = 3                          | **3**          |
| **Epistemic Risk**           | none = 0, low = 1, medium = 2, high = 3                                  | **3**          |
| **Decision Risk**            | none = 0, low = 1, medium = 2, high = 3                                  | **3**          |
| **Recoverability (inverse)** | easy = 1, partial = 2, hard = 3, redesign = 4 (harder = higher priority) | **4**          |

*Maximum score: 21. Target: resolve gaps with score ≥ 14 before any
deployment milestone.*

**4. Example Entry**

|                          |                                                                                                                                                                       |
|--------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **GAP-ID**               | GAP-202604-001                                                                                                                                                        |
| **Title**                | Missing hidden-principal claim-state model in posting cluster                                                                                                         |
| **Gap Type (primary)**   | G — Epistemic Gap                                                                                                                                                     |
| **Gap Type (secondary)** | H — Provenance Gap, C — Boundary Gap                                                                                                                                  |
| **Affected Modules**     | SARO, ORG, PostingEpistemics (missing)                                                                                                                                |
| **Observed Symptom**     | "Principal employer" field in Finnish agency postings has no clean representation when employer is unnamed. Forced into ORG with no confidence or verification state. |
| **Evidence Source**      | Real-data instantiation pass, Posting P003, Section B, H1 hypothesis                                                                                                  |
| **Evidence Date**        | 2026-04-10                                                                                                                                                            |
| **Hypothesis Confirmed** | true — H1                                                                                                                                                             |
| **Operational Impact**   | 3                                                                                                                                                                     |
| **Frequency**            | pervasive                                                                                                                                                             |
| **Scope**                | cross-module                                                                                                                                                          |
| **Epistemic Risk**       | high                                                                                                                                                                  |
| **Decision Risk**        | high                                                                                                                                                                  |
| **Remediation**          | Add pe:HiddenPrincipalState vocabulary and pe:hiringPrincipalClaim pattern to PostingEpistemics.ttl                                                                   |
| **Status**               | open                                                                                                                                                                  |

**5. Ledger Governance Rules**

- Every gap must be entered within 48 hours of detection.

- A gap may not be closed without a passing test result cited as
  resolution evidence.

- Deferred gaps must carry a deferral reason and a re-evaluation date.

- Rejected gaps must carry a rejection reason (e.g. "not an ontology gap
  — data issue").

- The ledger must be reviewed at every architecture checkpoint.

- Any remediation that closes a gap must be followed by import
  conservativity testing before the gap is marked resolved.

- Gap IDs are permanent. Closed gaps remain in the ledger; they are not
  deleted.

**6. Implementation Formats**

The gap ledger may be maintained in any of the following formats. Choose
one authoritative format and do not duplicate.

- YAML file in repository (gaps/ledger.yaml) — recommended for version
  control and CI integration.

- RDF/Turtle (gaps/ledger.ttl) — for graph-native integration and SPARQL
  querying.

- Structured Markdown table (gaps/LEDGER.md) — for human-readable
  review.

- Spreadsheet — acceptable for early-phase work only; migrate to YAML or
  RDF as the ledger grows.
