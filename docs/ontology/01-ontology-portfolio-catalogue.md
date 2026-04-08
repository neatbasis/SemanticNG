**ONTOLOGY PORTFOLIO CATALOGUE**

neatbasis Semantic System Architecture

*Version 1.0 · Reference Document*

**1. Purpose and Scope**

This catalogue defines the authoritative inventory of ontologies and
vocabularies in the neatbasis semantic system portfolio. Each entry
specifies the layer, type, authority, non-authority boundaries, key
entities, alignment targets, import strategy, and operational status.

The catalogue is the primary reference for: (a) determining which
ontology owns which distinction, (b) governing cross-layer connections,
and (c) controlling portfolio drift. It is a living document maintained
in lockstep with the gap ledger.

**2. Layered Architecture Overview**

The portfolio is organized into eleven layers. The ordering reflects
dependency direction: lower layers are more foundational and may not
import from higher layers without explicit justification.

- Layer 1: Formal Substrate

- Layer 2: Observation and State

- Layer 3: Time and Provenance

- Layer 4: Artifact and Knowledge Resources

- Layer 5: Agents and Organizations

- Layer 6: Capability, Competence and Work

- Layer 7: Publication and Interchange

- Layer 8: Architecture and Mission Alignment

- Layer 9: Mid-Level Grounding (fork decision required)

- Layer 10: Exchange-Model Alignment

- Layer 11: Local Extensions

**3. Portfolio Entries by Layer**

**3.x Formal Substrate**

|                                             |                                                                                                 |
|---------------------------------------------|-------------------------------------------------------------------------------------------------|
| **RDF / RDFS / OWL** \[ rdf / rdfs / owl \] |                                                                                                 |
| **Layer**                                   | Formal Substrate                                                                                |
| **Type**                                    | Foundational formal language                                                                    |
| **Authority**                               | Graph representation; typing; subclass/property semantics; formal logical expression            |
| **Non-authority**                           | Domain meaning; closed-world validation; portfolio governance                                   |
| **Key Classes / Entities**                  | rdf:Property, rdfs:Class, owl:Class, owl:ObjectProperty, owl:DatatypeProperty, owl:disjointWith |
| **Alignment Targets**                       | Everything depends on it                                                                        |
| **Import Strategy**                         | Direct import — all modules depend on this                                                      |
| **Status**                                  | Foundational — core                                                                             |

|                            |                                                                                                  |
|----------------------------|--------------------------------------------------------------------------------------------------|
| **SKOS** \[ skos \]        |                                                                                                  |
| **Layer**                  | Formal Substrate                                                                                 |
| **Type**                   | Concept scheme vocabulary                                                                        |
| **Authority**              | Concept hierarchies; preferred/alternative labels; broader/narrower/related mappings; crosswalks |
| **Non-authority**          | Competence possession; job-post artifact semantics; provenance; temporal validity by default     |
| **Key Classes / Entities** | skos:Concept, skos:ConceptScheme, skos:Collection                                                |
| **Alignment Targets**      | ESCO; local capability concept schemes; standards via BIBO/DC Terms                              |
| **Import Strategy**        | Direct import — wherever concept schemes or taxonomies appear                                    |
| **Status**                 | Foundational — core                                                                              |

**3.x Observation and State**

|                            |                                                                                             |
|----------------------------|---------------------------------------------------------------------------------------------|
| **SOSA** \[ sosa \]        |                                                                                             |
| **Layer**                  | Observation and State                                                                       |
| **Type**                   | Lightweight observation pattern                                                             |
| **Authority**              | Observations; results; observed properties; procedures; features of interest                |
| **Non-authority**          | Final interpreted state; mission/task semantics; competence; canonical truth of context     |
| **Key Classes / Entities** | sosa:Observation, sosa:Sensor, sosa:Result, sosa:FeatureOfInterest, sosa:ObservableProperty |
| **Alignment Targets**      | SSN; PROV-O; OWL-Time; GeoSPARQL; local context/mission state layers                        |
| **Import Strategy**        | Direct import — foundational for all context and sensing systems                            |
| **Status**                 | Foundational — core                                                                         |

|                            |                                                                        |
|----------------------------|------------------------------------------------------------------------|
| **SSN** \[ ssn \]          |                                                                        |
| **Layer**                  | Observation and State                                                  |
| **Type**                   | Richer sensing system semantics                                        |
| **Authority**              | Sensing systems; deployment context; richer observation infrastructure |
| **Non-authority**          | Final operational or user state; mission logic; competence             |
| **Key Classes / Entities** | ssn:System, ssn:Deployment, ssn:Property                               |
| **Alignment Targets**      | SOSA; PROV-O; GeoSPARQL; operational context layer                     |
| **Import Strategy**        | Direct import — full sensing infrastructure layer                      |
| **Status**                 | Foundational — core                                                    |

|                            |                                                                              |
|----------------------------|------------------------------------------------------------------------------|
| **GeoSPARQL** \[ geo \]    |                                                                              |
| **Layer**                  | Observation and State                                                        |
| **Type**                   | Spatial semantics                                                            |
| **Authority**              | Features; geometries; topological spatial relations; spatial query semantics |
| **Non-authority**          | Temporal validity; provenance; observation interpretation by itself          |
| **Key Classes / Entities** | geo:Feature, geo:Geometry, geo:SpatialObject                                 |
| **Alignment Targets**      | OWL-Time (by profile); SOSA/SSN; postings; org facilities; mission modules   |
| **Import Strategy**        | Direct import — required wherever location is reason-able                    |
| **Status**                 | Foundational — core                                                          |

**3.x Time and Provenance**

|                            |                                                                               |
|----------------------------|-------------------------------------------------------------------------------|
| **OWL-Time** \[ time \]    |                                                                               |
| **Layer**                  | Time and Provenance                                                           |
| **Type**                   | Temporal ontology                                                             |
| **Authority**              | Instants; intervals; durations; temporal ordering; temporal position          |
| **Non-authority**          | Provenance activity semantics; domain meaning of events; spatial extent       |
| **Key Classes / Entities** | time:Instant, time:Interval, time:TemporalEntity                              |
| **Alignment Targets**      | PROV-O; SSN/SOSA; postings; mission/task state models; role validity patterns |
| **Import Strategy**        | Direct import — required wherever time qualification is mandatory             |
| **Status**                 | Foundational — core                                                           |

|                            |                                                                                             |
|----------------------------|---------------------------------------------------------------------------------------------|
| **PROV-O** \[ prov \]      |                                                                                             |
| **Layer**                  | Time and Provenance                                                                         |
| **Type**                   | Provenance ontology                                                                         |
| **Authority**              | Source usage; activity; generation; attribution; derivation; provenance agents              |
| **Non-authority**          | Full actor identity structure; competence semantics; domain meaning of mission/task/posting |
| **Key Classes / Entities** | prov:Entity, prov:Activity, prov:Agent, prov:Plan                                           |
| **Alignment Targets**      | BIBO; SSN/SOSA; OWL-Time; local posting and mission extension modules                       |
| **Import Strategy**        | Direct import — all extracted or inferred facts must carry provenance                       |
| **Status**                 | Foundational — core                                                                         |

**3.x Artifact and Knowledge Resources**

|                            |                                                                                                    |
|----------------------------|----------------------------------------------------------------------------------------------------|
| **DC Terms** \[ dct \]     |                                                                                                    |
| **Layer**                  | Artifact and Knowledge Resources                                                                   |
| **Type**                   | Generic metadata vocabulary                                                                        |
| **Authority**              | Generic resource metadata: titles, identifiers, dates, creators, languages, references, part-whole |
| **Non-authority**          | Bibliographic-specific citation structure; extraction provenance; competence or mission semantics  |
| **Key Classes / Entities** | dcterms:BibliographicResource, dcterms:Standard                                                    |
| **Alignment Targets**      | BIBO; PROV-O; ontology catalogue artifact records; standards and governance docs                   |
| **Import Strategy**        | Direct import — portfolio-wide artifact metadata                                                   |
| **Status**                 | Core                                                                                               |

|                            |                                                                                                 |
|----------------------------|-------------------------------------------------------------------------------------------------|
| **BIBO** \[ bibo \]        |                                                                                                 |
| **Layer**                  | Artifact and Knowledge Resources                                                                |
| **Type**                   | Bibliographic/document ontology                                                                 |
| **Authority**              | Bibliographic document typing; citation graph; bibliographic identifiers and document structure |
| **Non-authority**          | Provenance generation; internal concept hierarchies; operational state                          |
| **Key Classes / Entities** | bibo:Document, bibo:Article, bibo:Standard, bibo:Report, bibo:Webpage, bibo:Specification       |
| **Alignment Targets**      | DC Terms; PROV-O; ontology catalogue entries; source documents and standards                    |
| **Import Strategy**        | Direct import — for any citable artifact in the graph                                           |
| **Status**                 | Core                                                                                            |

**3.x Agents and Organizations**

|                            |                                                                                            |
|----------------------------|--------------------------------------------------------------------------------------------|
| **FOAF** \[ foaf \]        |                                                                                            |
| **Layer**                  | Agents and Organizations                                                                   |
| **Type**                   | Lightweight person/agent identity                                                          |
| **Authority**              | Lightweight identity/profile/account representation                                        |
| **Non-authority**          | Organizational role structure; competence; provenance process role; mission responsibility |
| **Key Classes / Entities** | foaf:Person, foaf:Agent, foaf:Organization                                                 |
| **Alignment Targets**      | ORG; BIBO; Core-O; PROV-O (carefully)                                                      |
| **Import Strategy**        | Align only — keep thin; subordinate to ORG and PROV needs                                  |
| **Status**                 | Core — kept minimal                                                                        |

|                            |                                                                                                          |
|----------------------------|----------------------------------------------------------------------------------------------------------|
| **ORG** \[ org \]          |                                                                                                          |
| **Layer**                  | Agents and Organizations                                                                                 |
| **Type**                   | Organizational structure ontology                                                                        |
| **Authority**              | Organizations; sub-units; memberships; posts; structural roles                                           |
| **Non-authority**          | Competence possession; posting artifact semantics; provenance process semantics; mission execution state |
| **Key Classes / Entities** | org:Organization, org:OrganizationalUnit, org:Post, org:Membership                                       |
| **Alignment Targets**      | FOAF; PROV-O; SARO; mission participant structures                                                       |
| **Import Strategy**        | Direct import — for employer/recruiter/principal organizational structure                                |
| **Status**                 | Core                                                                                                     |

**3.x Capability, Competence and Work**

|                            |                                                                                               |
|----------------------------|-----------------------------------------------------------------------------------------------|
| **ESCO** \[ esco \]        |                                                                                               |
| **Layer**                  | Capability, Competence and Work                                                               |
| **Type**                   | Reference concept system (cross-layer)                                                        |
| **Authority**              | Canonical occupation and skill concept identifiers; multilingual labels and concept structure |
| **Non-authority**          | Possession claims; job-post artifact semantics; local market epistemic states; provenance     |
| **Key Classes / Entities** | ESCO Occupation, ESCO Skill, ESCO Qualification (as SKOS Concepts)                            |
| **Alignment Targets**      | SKOS; SARO; Core-O; local posting extraction mappings                                         |
| **Import Strategy**        | Align by reference — external concept registry, not imported OWL                              |
| **Status**                 | Core                                                                                          |

|                            |                                                                                                                 |
|----------------------------|-----------------------------------------------------------------------------------------------------------------|
| **Core-O** \[ coreo \]     |                                                                                                                 |
| **Layer**                  | Capability, Competence and Work                                                                                 |
| **Type**                   | Competence reference ontology                                                                                   |
| **Authority**              | Competence as possessed or required; proficiency; evidence-bearing competence structures; actor-side capability |
| **Non-authority**          | Posting artifact extraction; provenance generation; org structure; sensor observation                           |
| **Key Classes / Entities** | Competence, Skill, Knowledge, KSA (Knowledge/Skill/Attitude), Proficiency                                       |
| **Alignment Targets**      | ESCO; FOAF/ORG; local capability ontology; matching layer                                                       |
| **Import Strategy**        | Direct import — for competence claim and matching reasoning                                                     |
| **Status**                 | Core                                                                                                            |

|                            |                                                                                               |
|----------------------------|-----------------------------------------------------------------------------------------------|
| **SARO** \[ saro \]        |                                                                                               |
| **Layer**                  | Capability, Competence and Work                                                               |
| **Type**                   | Recruitment domain ontology                                                                   |
| **Authority**              | Posting-level recruitment semantics; job post requirements; recruitment-oriented structures   |
| **Non-authority**          | Org structure in depth; competence possession; provenance; epistemic states (unless extended) |
| **Key Classes / Entities** | JobPost, Skill, Qualification, User (recruitment context)                                     |
| **Alignment Targets**      | ESCO; ORG; BIBO; PROV-O; OWL-Time; local PostingEpistemics                                    |
| **Import Strategy**        | Direct import — primary posting/recruitment artifact model                                    |
| **Status**                 | Core                                                                                          |

**3.x Publication and Interchange**

|                             |                                                                                    |
|-----------------------------|------------------------------------------------------------------------------------|
| **Schema.org** \[ schema \] |                                                                                    |
| **Layer**                   | Publication and Interchange                                                        |
| **Type**                    | Web-facing lightweight vocabulary                                                  |
| **Authority**               | Web-interoperable job posting metadata; web document metadata                      |
| **Non-authority**           | Internal competence modeling; provenance; organizational detail; spatial reasoning |
| **Key Classes / Entities**  | schema:JobPosting, schema:Organization, schema:Person                              |
| **Alignment Targets**       | SARO; DC Terms                                                                     |
| **Import Strategy**         | Align only — outer publication layer                                               |
| **Status**                  | Core — publication surface                                                         |

**3.x Architecture and Mission Alignment**

|                            |                                                                                 |
|----------------------------|---------------------------------------------------------------------------------|
| **UAF / NAF** \[ uaf \]    |                                                                                 |
| **Layer**                  | Architecture and Mission Alignment                                              |
| **Type**                   | Architecture framework metamodel                                                |
| **Authority**              | Capabilities; operational activities; services; resources; mission architecture |
| **Non-authority**          | Sensor observation semantics; provenance process detail; competence possession  |
| **Key Classes / Entities** | uaf:Capability, uaf:OperationalActivity, uaf:Service                            |
| **Alignment Targets**      | PROV-O; OWL-Time; ORG; local MissionContext                                     |
| **Import Strategy**        | Align by reference — not direct dependency import                               |
| **Status**                 | Core — alignment target                                                         |

**3.x Mid-Level Grounding**

|                                            |                                                                                         |
|--------------------------------------------|-----------------------------------------------------------------------------------------|
| **CCO (Common Core Ontologies)** \[ cco \] |                                                                                         |
| **Layer**                                  | Mid-Level Grounding                                                                     |
| **Type**                                   | Maintained BFO-aligned mid-level suite                                                  |
| **Authority**                              | Agent, Event, Time, Quality, Artifact, and related mid-level modules (BFO-aligned)      |
| **Non-authority**                          | Domain meaning specific to jobs, missions, or sensing without extension                 |
| **Key Classes / Entities**                 | cco:Agent, cco:Event, cco:Artifact, cco:InformationBearingEntity                        |
| **Alignment Targets**                      | BFO; PROV-O; local mission and context layers                                           |
| **Import Strategy**                        | Align strategically — use if BFO/CCO mid-level family is chosen; fork decision required |
| **Status**                                 | Optional — BFO/CCO path decision required                                               |

**3.x Exchange-Model Alignment**

|                             |                                                                                    |
|-----------------------------|------------------------------------------------------------------------------------|
| **JC3IEDM / MIP** \[ jc3 \] |                                                                                    |
| **Layer**                   | Exchange-Model Alignment                                                           |
| **Type**                    | NATO operational exchange data model                                               |
| **Authority**               | Units; equipment; tasks; actions; locations; operational status exchange semantics |
| **Non-authority**           | Ontological truth in general sense; competence; provenance in W3C sense            |
| **Key Classes / Entities**  | Unit, Task, Action, Facility, Location (JC3IEDM entities)                          |
| **Alignment Targets**       | Local MissionContext; ORG; OWL-Time; GeoSPARQL                                     |
| **Import Strategy**         | Map only — do not import; express bridge mappings                                  |
| **Status**                  | Reference — interoperability alignment                                             |

**3.x Local Extensions**

|                                      |                                                                                                                                                                              |
|--------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Local PostingEpistemics** \[ pe \] |                                                                                                                                                                              |
| **Layer**                            | Local Extensions                                                                                                                                                             |
| **Type**                             | Local extension ontology                                                                                                                                                     |
| **Authority**                        | Claim status for posting assertions; hidden principal semantics; inferred employer identity; source conflict; duplicate canonicalization; verification and confidence states |
| **Non-authority**                    | Raw source document representation; basic provenance machinery; organization identity itself; ESCO concept semantics                                                         |
| **Key Classes / Entities**           | pe:ClaimStatus, pe:HiddenPrincipalState, pe:PostingType, pe:DuplicateRelation, pe:SourceConflict                                                                             |
| **Alignment Targets**                | PROV-O; OWL-Time; SARO; ORG; BIBO; DC Terms; GeoSPARQL                                                                                                                       |
| **Import Strategy**                  | Local definition — thin extension, gap-ledger-motivated                                                                                                                      |
| **Status**                           | Active development                                                                                                                                                           |

|                                   |                                                                                                               |
|-----------------------------------|---------------------------------------------------------------------------------------------------------------|
| **Local MissionContext** \[ mc \] |                                                                                                               |
| **Layer**                         | Local Extensions                                                                                              |
| **Type**                          | Local extension ontology                                                                                      |
| **Authority**                     | Mission intent; objectives; tasks; effects; constraints; execution state; phases; readiness; state assertions |
| **Non-authority**                 | Sensor observation semantics; basic provenance machinery; org identity itself                                 |
| **Key Classes / Entities**        | mc:Mission, mc:Task, mc:Objective, mc:Effect, mc:Constraint, mc:MissionState, mc:Phase, mc:StateAssertion     |
| **Alignment Targets**             | PROV-O; OWL-Time; SSN/SOSA; ORG; GeoSPARQL; UAF/NAF (by reference)                                            |
| **Import Strategy**               | Local definition — open core with restricted extension point                                                  |
| **Status**                        | Planned                                                                                                       |

**4. Authority and Connection Rules**

1.  Rule 1: SSN/SOSA owns observation structure. No other ontology may
    claim to define what an observation is.

2.  Rule 2: PROV-O owns derivation lineage. All extracted or inferred
    facts must carry a recoverable PROV-O chain.

3.  Rule 3: OWL-Time owns explicit temporal qualification. Facts that
    change over time must be time-qualified using OWL-Time constructs or
    an approved portfolio pattern.

4.  Rule 4: ORG and FOAF own actor identity and structural roles. PROV-O
    Agent is a provenance role only, not an identity definition.

5.  Rule 5: ESCO owns reference concepts. It is the source of truth for
    canonical occupation and skill identifiers.

6.  Rule 6: Core-O owns competence claims. Actor-side capability
    modeling is Core-O territory, not ESCO.

7.  Rule 7: SARO owns posting/recruitment artifact semantics. It does
    not own epistemic uncertainty or hidden-principal semantics.

8.  Rule 8: PostingEpistemics owns posting-specific uncertainty,
    verification, interpretation, and canonicalization.

9.  Rule 9: MissionContext owns mission intent, objectives, tasks,
    effects, constraints, and execution state.

10. Rule 10: GeoSPARQL owns spatial representation and topological
    reasoning. String coordinates are ingestion state, not authoritative
    state.

11. Rule 11: No single ontology may become the semantic center of
    everything. Layered authority must be preserved.

**5. Maintenance Rules**

- Every new class or property must cite a gap ledger entry that
  motivated it.

- Every import or alignment change must be followed by import
  conservativity testing.

- Every catalogue entry must be reviewed when a new version of the
  referenced standard is published.

- Local extensions may not replicate semantics owned by imported
  standard ontologies.

- The mid-level alignment fork (BFO/CCO vs UFO/gUFO) must be resolved
  and recorded before MissionContext development advances beyond
  skeleton stage.
