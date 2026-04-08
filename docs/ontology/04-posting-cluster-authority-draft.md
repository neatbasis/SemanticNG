**POSTING CLUSTER AUTHORITY DRAFT**

v0 — Boundary and Authority Control Document

*neatbasis Ontology Portfolio · Version 0.1*

**1. Purpose**

This document defines the authority boundaries, mandatory
qualifications, and extension points for the ontology cluster that
models job postings in the neatbasis portfolio. Its function is to make
the instantiation pass sharp by answering: which ontology owns which
distinction, which facts must carry provenance, which must carry
temporal qualification, which should support spatial qualification, and
which unresolved distinctions belong in PostingEpistemics.ttl.

This is not a full ontology specification. It is a bounded architectural
control document for the posting domain.

**2. Core Modeling Principle**

A posting ecosystem contains at least three distinct layers of truth
that must not collapse into one node:

|           |                                 |                                                                                                     |
|-----------|---------------------------------|-----------------------------------------------------------------------------------------------------|
| **Layer** | **Name**                        | **Description**                                                                                     |
| **A**     | **Source Artifact Truth**       | What a particular source document or webpage says.                                                  |
| **B**     | **Canonical Opportunity Truth** | The portfolio's current best representation of the underlying opportunity.                          |
| **C**     | **Epistemic Truth State**       | How certain, verified, inferred, unresolved, stale, or conflicting the canonical interpretation is. |

**3. Authority Boundaries by Ontology**

**3.1 BIBO**

|                                                                                                                         |     |
|-------------------------------------------------------------------------------------------------------------------------|-----|
| **Owns**                                                                                                                |     |
| Source document / webpage / posting artifact as citable artifact; document-type distinctions; citation relations.       |     |
| **Does NOT own**                                                                                                        |     |
| Canonical job opportunity identity; employer truth; recruiter truth; extraction provenance; hidden-principal semantics. |     |

**3.2 DC Terms**

|                                                                                                        |     |
|--------------------------------------------------------------------------------------------------------|-----|
| **Owns**                                                                                               |     |
| Generic artifact metadata: title, identifier, issued/modified dates, language, references, part-whole. |     |
| **Does NOT own**                                                                                       |     |
| Bibliographic-specific citation structure; extraction provenance; posting semantics.                   |     |

**3.3 PROV-O**

|                                                                                                                                            |     |
|--------------------------------------------------------------------------------------------------------------------------------------------|-----|
| **Owns**                                                                                                                                   |     |
| Extraction activity; normalization activity; mapping activity; inference activity; derivation links; provenance agents.                    |     |
| **Does NOT own**                                                                                                                           |     |
| Domain semantics of job opportunities; organization structure beyond provenance-agent role; epistemic classification vocabulary by itself. |     |

**3.4 SARO**

|                                                                                                                                                                                               |     |
|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----|
| **Owns**                                                                                                                                                                                      |     |
| Posting-level recruitment semantics; requirements and qualifications as stated; recruitment-oriented structures.                                                                              |     |
| **Does NOT own**                                                                                                                                                                              |     |
| Source document identity as artifact; deep organization structure; hidden-principal epistemics; provenance process semantics; geometry/spatial reasoning; competence possession by candidate. |     |

**3.5 ORG**

|                                                                                                                                                        |     |
|--------------------------------------------------------------------------------------------------------------------------------------------------------|-----|
| **Owns**                                                                                                                                               |     |
| Organization identities; organizational units; structural positions and memberships; role-bearing structures.                                          |     |
| **Does NOT own**                                                                                                                                       |     |
| Confidence that an organization is the true hiring principal; publication artifact semantics; extraction process semantics; source claim truth status. |     |

**3.6 ESCO**

|                                                                                                                     |     |
|---------------------------------------------------------------------------------------------------------------------|-----|
| **Owns**                                                                                                            |     |
| Normalized occupation and skill concept identifiers; multilingual concept references; concept-level classification. |     |
| **Does NOT own**                                                                                                    |     |
| Raw textual skill mention; confidence of mapping by itself; competence possession; recruitment artifact semantics.  |     |

**3.7 OWL-Time**

|                                                                                                              |     |
|--------------------------------------------------------------------------------------------------------------|-----|
| **Owns**                                                                                                     |     |
| Posting publication date; validity interval; application deadline; temporal qualification of mutable claims. |     |
| **Does NOT own**                                                                                             |     |
| Why the fact exists; provenance activity semantics; spatial extent.                                          |     |

**3.8 GeoSPARQL**

|                                                                                                      |     |
|------------------------------------------------------------------------------------------------------|-----|
| **Owns**                                                                                             |     |
| Spatial feature and geometry representation; topological spatial relations; spatial query semantics. |     |
| **Does NOT own**                                                                                     |     |
| Temporal validity; provenance; hidden-principal logic.                                               |     |

**3.9 PostingEpistemics**

|                                                                                                                                                                                                 |     |
|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----|
| **Owns**                                                                                                                                                                                        |     |
| Claim status; hidden principal semantics; inferred employer identity; source conflict; duplicate-source identity claims; verification and confidence states specific to posting interpretation. |     |
| **Does NOT own**                                                                                                                                                                                |     |
| Raw source document representation; basic provenance machinery; organization identity itself; ESCO concept semantics; generic time or spatial semantics.                                        |     |

**4. Mandatory Distinction Set**

The posting cluster must distinguish at minimum the following entities
as separate nodes in the graph.

- Source Artifact: A concrete webpage, PDF, feed item, or other source
  document.

- Extracted Posting Record: A structured representation of what was
  extracted from a particular source artifact.

- Canonical Job Opportunity: The currently best-resolved representation
  of the underlying opportunity, potentially aggregated across multiple
  sources.

- Publishing Organization: The organization that published the posting
  artifact.

- Recruiting Intermediary: An organization acting as recruiter, staffing
  intermediary, or agency.

- Hiring Principal: The organization for which the role is ultimately
  being filled, whether explicit, hidden, inferred, or unresolved.

- Occupational Concept: Normalized ESCO occupation mapping.

- Skill Mention: The raw requirement phrase as expressed in the posting.

- Skill Concept Mapping: Normalized mapping from the raw mention to ESCO
  or another controlled concept.

- Validity Interval: The time interval during which the posting or claim
  is considered active/relevant.

- Work Location: Where the work is to be performed.

- Publication Jurisdiction: Where the source artifact originates or is
  legally situated.

- Claim Status: Whether something is source-asserted, verified,
  inferred, unresolved, contradicted, stale, or superseded.

- Duplicate-Source Identity Relation: The relation that multiple source
  artifacts are manifestations of the same underlying opportunity.

**5. Claim-State Model**

PostingEpistemics.ttl must define these claim-state values as a
controlled vocabulary.

|                                   |                                                              |                    |
|-----------------------------------|--------------------------------------------------------------|--------------------|
| **State**                         | **Meaning**                                                  | **Epistemic Risk** |
| **source_asserted**               | The source document makes this claim directly.               | Low                |
| **directly_observed_from_source** | Extracted verbatim from the source with no inference.        | Low                |
| **normalized_from_source**        | Extracted and mapped to a controlled vocabulary (e.g. ESCO). | Low–Medium         |
| **inferred**                      | Derived by rule or model from one or more sources.           | Medium             |
| **verified**                      | Corroborated by an independent source or manual check.       | Low                |
| **unverified**                    | Not yet assessed against independent evidence.               | High               |
| **unresolved**                    | Competing claims exist with no current resolution.           | High               |
| **contradicted**                  | Directly contradicted by another source.                     | High               |
| **stale**                         | Previously valid; may no longer apply.                       | Medium–High        |
| **superseded**                    | Replaced by a newer canonical assertion.                     | Low (archived)     |

**6. Mandatory Provenance Facts**

The following facts must not exist in the graph without a recoverable
provenance chain to a source artifact and extraction/inference activity.

- Extracted employer name

- Extracted recruiter/intermediary name

- Extracted skill mention

- Normalized ESCO occupation mapping

- Normalized ESCO skill mapping

- Inferred hiring principal

- Canonical duplicate resolution

- Salary extraction

- Posting validity interval (if inferred)

- Geocoded work location

- Speculative-posting classification

- Hidden-principal classification

- Any verification state not directly stated in source

**7. Mandatory Time-Qualified Facts**

The following facts must carry explicit temporal qualification using
OWL-Time constructs or an approved portfolio pattern.

- Source publication date

- Source modification date

- Posting validity interval

- Application deadline

- Salary validity where source-specific

- Organization role in a specific posting

- Hidden-principal inference freshness

- Duplicate-source resolution freshness

- Verification status validity

- Geocoded location freshness if derived

- Skill/occupation mapping version context

**8. Spatial Upgrade Path**

String location values are permitted as ingestion state only. The
following facts must support upgrade to GeoSPARQL feature/geometry form
for any use case requiring spatial reasoning.

- Work location

- Employer office location

- Recruiter office location

- Publication jurisdiction

- Remote / hybrid / on-site region semantics

- Acceptable candidate region

- Labour-market region

- Municipality / county / country / EU-area scope

**9. Boundary Rules**

1.  Rule 1: A source artifact is not the same thing as a canonical job
    opportunity.

2.  Rule 2: An organization named in a posting is not automatically the
    hiring principal.

3.  Rule 3: A skill phrase in text is not the same thing as its ESCO
    concept mapping.

4.  Rule 4: A source claim is not the same thing as a verified fact.

5.  Rule 5: An observation/extraction result is not the same thing as an
    interpreted state assertion.

6.  Rule 6: A publishing organization is not automatically a recruiting
    intermediary; a recruiting intermediary is not automatically the
    hiring principal.

7.  Rule 7: A posting validity interval is distinct from: publication
    date / extraction timestamp / indexing timestamp / verification
    timestamp.

8.  Rule 8: A textual location string is not the same thing as a
    resolved spatial feature/geometry.

**10. Instantiation Pass Hypotheses**

These hypotheses must be actively tested against 5–10 Finnish job
postings using the Posting Annotation Worksheet (Document 5).

|        |                         |                                                                                                                                            |
|--------|-------------------------|--------------------------------------------------------------------------------------------------------------------------------------------|
| **ID** | **Area**                | **Hypothesis**                                                                                                                             |
| **H1** | **Hidden principal**    | Current stack lacks a clean representation for hidden or partially inferable hiring principal.                                             |
| **H2** | **Claim status**        | Current stack lacks a clean representation for claim status on posting facts (asserted / verified / inferred / unresolved / contradicted). |
| **H3** | **Source vs canonical** | Current stack lacks a clean pattern for distinguishing: source posting artifact / extracted record / canonical job opportunity.            |
| **H4** | **Time-bounded truth**  | Current stack lacks consistent support for time-bounded truth in posting facts.                                                            |
| **H5** | **Spatial semantics**   | Current stack lacks consistent support for posting-relevant spatial semantics beyond string storage.                                       |
| **H6** | **Duplicate sources**   | Current stack lacks a clean pattern for duplicate postings across sources.                                                                 |
| **H7** | **Source conflict**     | Current stack lacks a clean pattern for source conflict without forced premature collapse.                                                 |

**11. PostingEpistemics.ttl Design Rules**

- Imports directly: PROV-O, OWL-Time, SARO, ORG, BIBO, DC Terms.

- Aligns by reference: ESCO (indirectly through posting/skill mapping
  structures), GeoSPARQL (where claim-state concerns involve resolved
  locations).

- Must not duplicate: generic provenance semantics, organization
  identity semantics, document semantics, or SARO recruitment semantics.

- Every class and property must reference the gap ledger entry (by ID)
  that motivated its addition.

- Version 0 skeleton only after the instantiation pass is complete.
