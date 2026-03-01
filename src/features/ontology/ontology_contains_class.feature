Feature: Ontology
  In order to understand knowledge
  As the SemanticNG core
  I want do cool stuff

  Scenario: Ontology contains class
    Given an ontology file "pizza.owl"
    Then class "Margherita" should exist
