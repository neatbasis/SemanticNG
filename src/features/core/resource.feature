Feature: Resource envelope
  In order to store knowledge immutably and auditably
  As the SemanticNG core
  I want every stored item to be a Resource with DC metadata, payload, integrity, and optional namespaced extensions

  Background: Resource store
    Given a Resource store that is append-only
    
  Scenario: Create a minimal Resource
    When I create a Resource with dc:type "Event"
    And with dc:created "2026-02-14T10:00:00Z"
    And with dc:source "channel:discord"
    And with payload:
      """
      {"text":"they're here"}
      """
    And I build the Resource
    Then the Resource MUST contain meta, payload, integrity
    And integrity.content_hash MUST be a sha256 of canonical content
