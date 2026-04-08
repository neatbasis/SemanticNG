# Idea Selection Protocol

## Purpose

This document defines a disciplined way to choose problems worth working on without drifting into handwavy taste or vague “interestingness”.

The goal is to preserve the strengths of discernment — beauty, leverage, elegance, inevitability, timing — while making the decision process explicit enough to inspect, compare, and improve.

This is especially useful when selecting among problems that are:

- difficult
- partially open
- high-leverage
- aesthetically compelling
- not obviously reducible to a simple checklist

---

## Core principle

Choose the problem where an invariants-first, testable, constructive approach can turn a beautiful theory-level idea into a falsifiable computational object in a regime that is newly tractable.

This means preferring ideas that are not only interesting, but also:

- structurally clear
- testable
- leverage-producing
- timely
- and small enough to admit a real first wedge

---

## Decision categories

### 1. Good idea

A good idea has:

- clear boundary
- crisp invariants
- measurable progress
- low ambiguity

Questions:

- What is the smallest statement of the problem that still matters?
- What is the failure mode if the idea is wrong?
- What invariants make the problem non-handwavy?
- What would count as evidence of progress?

### 2. Beautiful idea

A beautiful idea has:

- inevitability
- compression
- reusability
- a small number of moves that explain many things

Questions:

- What does this idea compress?
- What does it unify?
- What becomes simpler if this idea works?
- What is the smallest primitive or theorem that makes the rest feel inevitable?

### 3. Worth spending time on

A worthwhile idea creates compounding returns.

Questions:

- If this works, what becomes easy that is currently hard?
- Does it create a reusable tool, language, protocol, or verifier?
- Will it still matter after nearby theory or tooling evolves?
- Does it improve future thinking, not just one result?

### 4. Interesting, difficult, and timely

A strong candidate is not just unsolved, but unsolved in a way that may now admit a tractable wedge.

Questions:

- Why has this not been solved already?
- What has changed that makes progress more plausible now?
- What is the smallest wedge that is solvable now?
- What part is still genuinely open versus merely poorly packaged?

---

## Candidate problem portfolio method

Do not pick scope immediately.

Instead, define 3–6 candidate problems and compare them using the same template.

For each candidate, record:

- statement
- why it matters
- why it is hard
- why now
- success criteria
- risks and falsifiers

This helps avoid premature commitment and turns taste into explicit comparison.

---

## Candidate template

## Candidate P\#

- **One-sentence statement**
- **Beauty claim:** what it unifies or compresses
- **Leverage claim:** what it unlocks
- **Hardness claim:** what has historically blocked it
- **Now claim:** what makes it newly tractable
- **Definition of Done:** measurable deliverables and tests
- **Falsifiers:** what would show the idea is wrong, weak, or not worth pursuing

---

## Scoring rubric

Score each candidate from 0–5 on each dimension.

### 1. Constraint elegance

Few axioms, many consequences.

### 2. Invariant richness

Many falsifiable checks and meaningful test surfaces.

### 3. Generative leverage

Solving it unlocks future work, tools, or frameworks.

### 4. Timeliness

Something about the current moment makes it newly workable.

### 5. Open-ness

It is not already fully solved in the form that matters here.

### 6. Feasible wedge

There is a plausible v0.2 or v0.3 version that can be built and tested.

---

## Solved-ness classification

Many “unsolved” problems are solved in one sense and unsolved in another.

Separate the following:

- solved in theory
- solved in examples
- solved algorithmically
- solved with verifiable invariants
- solved as reusable software

A problem can still be worth doing if theory exists but there is no:

- reusable computational method
- verifier-backed implementation
- contract-driven framework
- durable testable tooling layer

That is a valid unsolved category.

---

## Now-ness signals

A problem is more timely when there is a clear reason it is more tractable now than before.

Examples of now-ness signals:

- symbolic tooling has improved
- exact arithmetic or algebra systems are mature enough
- property-based or metamorphic testing can verify nontrivial invariants
- definitions can now be encoded as executable gates
- the surrounding research landscape has shifted enough to make the timing favorable

---

## Example candidate directions

These are examples of the kind of problems that fit this protocol.

### 1. Constructive boundary-reconstruction solver

**Statement:** Given a boundary/facet description, reconstruct the canonical object directly from constraints and residues without relying on triangulation as the primary method.

**Why it is compelling:** It turns a derived representation into a constraint-driven constructive object.

**Why it is hard:** Stability, normalization, and constraint sufficiency are nontrivial.

**Why now:** Exact arithmetic, symbolic tooling, and invariant-driven testing make a first wedge plausible.

### 2. Stronger operationalization of log-singularity criteria

**Statement:** Implement symbolic criteria that distinguish genuine dlog singularities from expressions that only superficially resemble boundary poles.

**Why it is compelling:** It upgrades heuristic checks into definition-level enforcement.

**Why it is hard:** Coordinate dependence, cancellations, and local normal form issues are subtle.

**Why now:** Chart comparisons, residue checks, and symbolic test machinery make this operationally approachable.

### 3. Drift-proof verifier framework for canonical forms

**Statement:** Build a system where scope changes automatically surface required theory, engine, and test amendments.

**Why it is compelling:** It converts conceptual drift into governed evolution.

**Why it is hard:** The challenge is meta-architectural rather than purely mathematical.

**Why now:** Invariant-first engineering and explicit governance make this form of evolution-management feasible.

---

## Practical process

A lightweight working process:

1. Write 3–6 candidate problems.
2. Classify each candidate by solved-ness.
3. Score each candidate with the rubric.
4. Pick the top 1–2.
5. Define a concrete v0.2 or v0.3 wedge.
6. Update scope and purpose documents to reflect the choice.

---

## Selection rule

If forced to reduce everything to one rule:

Choose the problem where a beautiful theory-level definition can be turned into a falsifiable, reusable, invariants-first computational object in a regime that is newly tractable.

---

## Intended use

Use this document when:

- choosing the next research direction
- refining scope
- testing whether a problem is worth sustained attention
- distinguishing “beautiful but vague” from “beautiful and buildable”
- preventing drift into problems that are interesting but poorly framed

This protocol is not meant to replace judgment.

It is meant to make judgment inspectable.
