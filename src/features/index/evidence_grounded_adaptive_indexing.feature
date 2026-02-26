Feature: Evidence-grounded adaptive indexing (happy path)
  In order to unlock compounding retrieval quality over time
  As the SemanticNG indexing engine
  I want to ingest a Dublin Core Resource, propose a schema via a dense interpreter,
  validate it against an ontology, and persist structured outputs for sparse search

  Background:
    Given an append-only Resource store
    And a sparse index
    And an ontology registry
    And a schema registry with versioning
    And a dense interpreter configured for schema proposals

  Scenario: Ingest a DC Resource and persist a validated schema-derived artifact
    Given an ontology "core" with concepts:
      """
      {
        "Concepts": ["Person", "Organization", "Event", "Place", "Claim"],
        "Relations": ["mentions", "locatedAt", "affiliatedWith"]
      }
      """
    And a schema "Event.v1" mapped to ontology "core" with required fields:
      """
      {
        "type": "Event",
        "required": ["name", "startDate"],
        "optional": ["location", "organizer", "participants", "about"]
      }
      """
    And a Dublin Core Resource with:
      | dc:type       | Document            |
      | dc:created    | 2026-02-14T10:00:00Z |
      | dc:source     | channel:discord     |
      | dc:format     | text/plain          |
    And with payload text:
      """
      Meetup: SemanticNG hack night at Maria 01 on Feb 20, 18:00. Organizer: Hacklair.
      """
    When I ingest the Resource
    Then the Resource MUST be persisted immutably with an integrity content_hash

    When I request a schema proposal from the dense interpreter using ontology "core"
    Then the proposal MUST include a schema_id and a structured extraction
    And the proposal MUST cite evidence spans from the payload text
    And the proposed schema_id MUST be "Event.v1"

    When I validate the proposal against the ontology "core" and schema "Event.v1"
    Then validation MUST succeed
    And the extracted fields MUST satisfy required fields for "Event.v1"

    When I materialize a structured Artifact from the validated extraction
    Then the Artifact MUST be persisted as a new immutable Resource
    And the Artifact dc:type MUST be "Event"
    And the Artifact MUST include a link to the source Resource identifier
    And the Artifact MUST include evidence spans for each extracted field

    When I update the sparse index from the persisted Artifact
    Then the sparse index MUST contain the Artifact identifier
    And searching for "hack night" MUST return the Artifact in the top results
    And searching for "Maria 01" MUST return the Artifact in the top results

  Scenario: Ingest a DC Resource and record schema usage metrics
    Given an ontology "core" with concepts:
      """
      {
        "Concepts": ["Event"],
        "Relations": []
      }
      """
    And a schema "Event.v1" mapped to ontology "core" with required fields:
      """
      {
        "type": "Event",
        "required": ["name", "startDate"]
      }
      """
    And a Dublin Core Resource with:
      | dc:type       | Document            |
      | dc:created    | 2026-02-14T10:00:00Z |
      | dc:source     | channel:discord     |
      | dc:format     | text/plain          |
    And with payload text:
      """
      Meetup: SemanticNG hack night at Maria 01 on Feb 20, 18:00.
      """
    When I ingest the Resource
    And I request a schema proposal from the dense interpreter using ontology "core"
    And I validate the proposal against the ontology "core" and schema "Event.v1"
    And I materialize a structured Artifact from the validated extraction
    Then schema usage metrics MUST be updated for "Event.v1"
    And the schema usage record MUST include:
      | metric                  |
      | last_used_at            |
      | successful_validations  |
      | avg_confidence          |
