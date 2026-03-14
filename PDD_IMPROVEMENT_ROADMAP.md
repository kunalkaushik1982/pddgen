# PDD Improvement Roadmap

## Goal

Improve the generated PDD so it looks and reads like a professional enterprise document, not just extracted process output.

The focus areas are:

- document structure
- content quality
- visual quality
- reviewability
- automation-specific intelligence

## Phase 1: Professional PDD Structure

### Objective

Make the exported document look like a real PDD without changing the core extraction pipeline too much.

### Build in this phase

- formal document sections
- stronger `AS-IS` section structure
- document metadata
- business rules section
- assumptions / dependencies section
- cleaner template and wording

### Suggested document sections

1. Document overview
2. Process summary
3. Applications involved
4. `AS-IS` process overview
5. `AS-IS` step details
6. Business rules
7. Assumptions / dependencies
8. Open questions

### Why this comes first

- highest visible business impact
- fastest way to improve stakeholder confidence
- minimal change to the current architecture

## Phase 2: Better Process Intelligence

### Objective

Make the PDD more useful for BA, dev, and automation lead review.

### Build in this phase

- `TO-BE` draft section
- automation scope section
- exception handling section
- grouping of related steps into sub-processes
- AI-assisted wording cleanup

### Suggested additions

1. `TO-BE` suggested process
2. Automation opportunities
3. Inputs / outputs
4. Validations
5. Exception scenarios

### Recommendation

Do not auto-generate `TO-BE` as final truth.

Use:

- `AI-suggested TO-BE`
- clearly marked as draft
- editable by BA before final export

## Phase 3: Diagram and Visual Intelligence

### Objective

Improve document comprehension and make the PDD look more professional through visual flow representation.

### Build in this phase

- generated process flow diagram
- screenshot strategy for key evidence points
- optional diagram review before export

### Deliverables

- embedded flow diagram in DOCX/PDF
- downloadable diagram image
- clearer visual summary of the process

## Diagram Generation Strategy

## Recommended approach

Use a deterministic local diagram renderer. Do not depend on direct image generation from AI.

Best pipeline:

1. extract structured process steps
2. build a diagram model
3. render locally
4. embed into DOCX/PDF

### Diagram model should contain

- nodes
- edges
- optional decision labels
- optional grouped step blocks

## Option 1: Deterministic diagram generation

### How it works

- convert extracted steps into a simple graph
- render using a local tool

### Rendering candidates

- Mermaid
- Graphviz

### Pros

- no extra AI cost
- deterministic output
- easy to debug
- good starting point

### Cons

- limited process understanding
- weaker branching support unless added explicitly

### Recommendation

Start here for version 1.

## Option 2: OpenAI-assisted diagram specification

### How it works

- send structured steps to OpenAI
- ask it to return a diagram specification such as:
  - Mermaid
  - Graphviz DOT
  - node/edge JSON
- render locally afterward

### Pros

- can infer cleaner business-level nodes
- can identify decision points
- can improve labels and grouping

### Cons

- extra AI cost
- needs validation
- possible hallucination if prompts are weak

### Recommendation

Use OpenAI for reasoning, not final rendering.

## Option 3: Direct AI image generation

### Recommendation

Do not use this for enterprise PDD flow diagrams.

### Why not

- poor determinism
- difficult to edit
- hard to standardize
- weak auditability

## Final recommendation for diagrams

### Short term

Use:

- deterministic local diagram generation
- Graphviz or Mermaid

### Medium term

Use OpenAI to:

- simplify steps into business-level nodes
- identify decision points
- generate diagram spec

Then still render locally.

## Technology recommendation

### If speed of implementation matters more

Use:

- Mermaid

### If export control and rendering consistency matter more

Use:

- Graphviz

### Recommended choice for this app

Use:

- Graphviz for final export quality

## Suggested implementation order

1. strengthen exported PDD structure
2. improve `AS-IS` formatting
3. add `TO-BE` suggested section
4. add basic process flow diagram
5. improve exception and automation scope sections
6. enhance wording and screenshot strategy

## Summary

The best next direction is:

- first improve document structure
- then improve process intelligence
- then add deterministic diagram generation

For diagrams:

- no separate diagram API is required initially
- OpenAI can help generate the diagram specification
- final rendering should remain local and deterministic
