# Master Plan: AI-Assisted PDD Drafting for RPA Discovery

## 1. App Overview and Objectives

### Working Vision
Build an internal enterprise application that helps RPA Business Analysts generate a high-quality first draft of a Process Design Document (PDD) from discovery artifacts such as process walkthrough recordings, meeting transcripts, and a standard PDD template.

The system should behave like an experienced technical drafter: it prepares an accurate and well-structured first draft that a Business Analyst can validate and refine quickly, rather than attempting to replace human judgment.

### Primary Objective
Reduce the time spent creating a PDD from scratch by converting discovery evidence into a structured, reviewable, exportable first draft.

### Success Definition
The product succeeds if it reduces the BA effort for one PDD from several hours of manual documentation to a short review-and-correction workflow, while preserving trust in the resulting document.

### Core Outcome for Version 1
Generate a high-quality first draft of the `AS-IS` section of the PDD, with:

- Structured process steps
- Proposed screenshots mapped to steps
- Timestamps for traceability
- Detected user actions such as click, type, copy, paste, navigation
- Suggested business rules and notes extracted from transcript evidence
- Output aligned to the team's standard PDD template

`TO-BE` should remain outside the primary scope for version 1, except for optional clearly labeled suggestions where evidence is strong.

## 2. Why This Product Matters

### Business Problem
In current RPA discovery work, Business Analysts attend process walkthrough sessions, collect recordings and transcripts, and then manually create the PDD. This is time-intensive, repetitive, and highly detail-sensitive.

The PDD is a source-of-truth artifact for the automation development team. If it is incomplete, inaccurate, or poorly structured, downstream automation work becomes slower and riskier.

### Strategic Value
This product is not only about document generation. It also creates a structured understanding of business processes by learning:

- Application context
- User actions
- Screen navigation
- Data movement
- Business rules
- Decision points

That structured process understanding can later support adjacent capabilities such as process mining assistance, automation design acceleration, and eventually partial workflow generation.

## 3. Target Audience

### Primary User
Business Analyst in the RPA delivery team.

### Why the BA Is the Right First User
The BA:

- Attends discovery sessions
- Owns process understanding
- Currently spends the most time producing the PDD
- Validates the document before it reaches the development team

If the product fits the BA workflow well, adoption is practical and immediate.

### Secondary Users

- Automation Developers who consume the PDD
- Automation Leads who review delivery quality or team productivity

These users benefit from better documentation, but they are not the primary workflow owner in version 1.

## 4. Product Scope for Version 1

### In Scope

- Internal enterprise-only deployment
- Single-user BA workflow
- Upload of required discovery artifacts
- AI-assisted extraction of process steps from video and transcript
- Screenshot proposal tied to steps and timestamps
- Intermediate transcript intelligence for business rules and supporting notes
- Confidence-aware drafting
- Step-review workspace for validation and correction
- Moderate in-app editing before export
- Export to editable DOCX using the standard team template
- Structured internal representation of process data used to render the DOCX

### Required Inputs

- Video recording of the process walkthrough
- Transcript of the session
- Standard PDD template

### Optional Supporting Inputs

- SOP or existing process document
- Process diagram or flow
- Separate screenshots
- Business rules notes
- Sample PDDs

Optional inputs should improve completeness and confidence, but not be required to start the workflow.

### Explicitly Out of Scope for Version 1

- Full automatic final-submission PDD generation
- Full `TO-BE` authoring
- Multi-user collaboration workflows
- Full in-app document editing comparable to Word
- Broad process support for highly judgment-driven or loosely structured business activities
- Enterprise SSO in the first pilot phase

## 5. Ideal User Workflow

### End-to-End Workflow

1. Business Analyst uploads the process video, transcript, and standard PDD template.
2. The system analyzes the inputs and builds a structured draft of the `AS-IS` process.
3. The system proposes:
   - Ordered steps
   - Application names where detectable
   - User actions
   - Source-data references where inferable
   - Screenshots linked to timestamps
   - Suggested business rules and notes from transcript evidence
4. The BA enters a step-review workspace.
5. The BA reviews each step with evidence, including screenshot, timestamp, and transcript support.
6. The BA edits, merges, splits, reorders, adds, or removes steps as needed.
7. The BA corrects screenshots or adds missing screenshots.
8. The BA reviews flagged uncertainties and inferred content.
9. The system renders the reviewed process into the standard PDD structure and exports an editable DOCX.
10. The final PDD is stored in the team's normal document repository, while the working draft remains in the app for traceability.

### Product Principle
The system should optimize for "review and refine" rather than "generate and hope."

## 6. Core Features and Functionality

### A. Artifact Intake

- Upload and manage required input files
- Associate all inputs with one PDD drafting session
- Validate that minimum required inputs are present
- Accept optional enrichment documents when available

### B. Process Extraction Engine

- Detect ordered steps from video and transcript
- Identify likely user actions such as:
  - Click
  - Type
  - Copy
  - Paste
  - Open
  - Navigate
  - Submit
- Detect probable application context where visible or referenced
- Attach time references to extracted events

### C. Screenshot Extraction and Mapping

- Auto-capture candidate screenshots for key steps
- Map screenshots to relevant step timestamps
- Support BA replacement or addition of screenshots
- Leave room for future click-target highlighting

### D. Transcript Understanding

- Use transcript evidence to enrich steps
- Suggest business rules
- Suggest source-data references
- Suggest decision points or process notes
- Separate evidence-backed statements from lower-confidence inference

### E. Step Review Workspace

- Display one structured step at a time or in sequence
- Show:
  - Step number
  - Application
  - Action
  - Screenshot
  - Timestamp
  - Supporting transcript excerpt if available
  - Confidence indicators
- Allow moderate editing:
  - Edit step text
  - Reorder steps
  - Merge steps
  - Split steps
  - Replace screenshot
  - Add screenshot
  - Add or adjust business notes
  - Mark unclear or missing content

### F. Confidence-Aware Drafting

- Flag low-confidence steps
- Flag weak screenshot matches
- Flag inferred business rules
- Flag likely missing information

This is essential for trust. The product should never present uncertainty as certainty.

### G. Document Rendering and Export

- Render validated content into the standard PDD template
- Produce editable DOCX output
- Preserve a structured internal representation for future reuse and extension

## 7. UI and UX Design Principles

### Product Shape
Human-in-the-loop web application optimized for Business Analysts.

### UX Priorities

- Clarity over complexity
- Traceability for every generated step
- Fast review, not deep technical analysis
- Minimal cognitive overhead
- Strong evidence visibility

### Key Screens

- Upload / intake screen
- Processing status screen
- Step-review workspace
- Export / finalize screen

### Step-Review Experience
The review workspace is the heart of the product. Each step should feel verifiable, not mysterious. The BA should quickly understand:

- What happened
- Where it happened
- Why the system believes that step exists
- Whether the content is high-confidence or needs review

### Editing Philosophy
The app should support structured corrections to the process model, not attempt to replicate a full document editor.

## 8. High-Level Technical Stack Recommendations

This section stays intentionally conceptual rather than implementation-specific.

### Recommended Architecture Approach
Use a modular internal web application with separate logical layers for:

- File intake and storage
- Media/transcript analysis
- Structured process extraction
- Human review workflow
- Document rendering and export

### Frontend Recommendation
Use a web application for the BA-facing interface.

#### Why

- Easiest fit for a single-user internal workflow
- Good match for upload, review, and export tasks
- Easier to evolve into broader enterprise usage later

### Backend Recommendation
Use a service-oriented backend that orchestrates analysis tasks and document generation.

#### Why

- Long-running video processing needs asynchronous orchestration
- Extraction, review state, and export should be separable concerns
- Easier to scale from pilot to department usage

### Data Storage Recommendation
Maintain structured process data in an internal application store, separate from raw file storage.

Use two conceptual storage layers:

- Artifact storage for recordings, screenshots, templates, and generated files
- Structured metadata storage for steps, timestamps, confidence, extracted rules, and review state

#### Why This Is the Best Recommendation
This supports the chosen `DOCX + structured internal representation` model and creates a foundation for future process intelligence.

### AI / Analysis Layer Recommendation
Use a pipeline approach rather than one monolithic AI prompt.

Suggested conceptual stages:

1. Ingest and normalize inputs
2. Analyze video and transcript separately
3. Correlate events across media and transcript
4. Build structured step candidates
5. Attach confidence and evidence
6. Render reviewed output into PDD format

#### Why This Is Better Than a Single-Step Approach

- Easier to reason about errors
- Better auditability
- Better trust
- Easier improvement path over time

### Deployment Recommendation
Internal enterprise deployment, optimized first for pilot usage and designed to grow to department-scale throughput.

## 9. Conceptual Data Model

The app should treat the PDD draft as a structured process package, not just a document.

### Core Entities

#### Draft Session
Represents one PDD generation workflow tied to one process documentation effort.

Likely contains:

- Session identifier
- Created date
- Status
- Owner
- Input artifact references
- Review progress
- Export history

#### Input Artifact
Represents uploaded evidence.

Types may include:

- Video
- Transcript
- Template
- SOP
- Diagram
- Screenshot

#### Process Step
Represents one extracted or edited step in the `AS-IS` process.

Likely fields:

- Step number
- Application name
- Action description
- Source-data note
- Timestamp
- Screenshot reference
- Confidence score or band
- Evidence references
- BA-edited flag

#### Business Rule / Process Note
Represents extracted or inferred rule-like content from transcript or supporting materials.

Likely fields:

- Text
- Related step(s)
- Evidence source
- Confidence indicator
- Inferred vs explicit marker

#### Review Annotation
Represents BA corrections or flags.

Examples:

- Missing step
- Unclear screenshot
- Low-confidence action corrected
- Rule removed
- Rule accepted

#### Output Document
Represents the rendered DOCX export and associated version metadata.

## 10. Security and Governance Considerations

### Deployment Constraint
The product must be designed for internal enterprise-only usage.

### Why Security Matters Here
Discovery recordings and transcripts may contain:

- Sensitive internal systems
- Business procedures
- Customer-related information
- Operational access details
- Confidential business logic

### Version 1 Security Posture

- Internal environment only
- Restricted artifact access at the infrastructure level
- Controlled pilot user group
- No user-level identity integration initially

### Tradeoff
Skipping identity integration accelerates the pilot, but limits auditability and broader governance readiness.

### Security Recommendations by Phase

#### Phase 1

- Controlled internal deployment
- Limit usage to a small approved BA group
- Secure storage for artifacts and outputs
- Retention policy for recordings, screenshots, and generated drafts

#### Phase 2

- Add enterprise identity integration
- Add role-based access
- Add stronger audit trail for who uploaded, reviewed, edited, and exported

### Additional Governance Needs

- Data retention rules
- Secure deletion policy
- Version history for draft outputs
- Logging for processing and export actions
- Environment separation for pilot vs broader deployment

## 11. Scalability and Operational Expectations

### Expected Initial Scale

- Pilot to department-scale design
- Approximately 30 to 50 PDDs per month
- Recording lengths from 30 minutes to 2 hours
- Mix of desktop and web application recordings

### Operational Implications

- Analysis jobs may take noticeable time and should be asynchronous
- The system should support background processing and status tracking
- Larger recordings will require careful handling of storage, processing time, and artifact generation

### Scalability Recommendation
Design the workflow so that artifact processing and document rendering can scale independently from the BA-facing review interface.

This prevents long-running analysis work from degrading review usability.

## 12. Key Product Assumptions

- The team uses a single standard PDD template
- Required evidence will normally include video, transcript, and template
- Version 1 focuses on highly structured desktop and web processes
- The BA is willing to review and refine a draft rather than expect a final perfect document
- Time saved is the primary business success metric

## 13. Key Risks and Mitigation Strategies

### Risk 1: Inaccurate Step Sequencing
If the extracted action order does not match the actual recording, trust collapses quickly.

#### Mitigation

- Keep the initial domain focused on structured processes
- Anchor each step to timestamps
- Provide visible evidence and easy reordering in review

### Risk 2: Wrong Screenshot-to-Step Mapping
If screenshots do not match referenced actions, the BA will reject the draft.

#### Mitigation

- Use screenshot proposals, not fixed truth
- Allow screenshot replacement and addition
- Flag low-confidence image matches

### Risk 3: Overconfident Business Rule Extraction
Transcript interpretation can easily become speculation.

#### Mitigation

- Use confidence-aware drafting
- Mark inferred rules separately from explicit statements
- Show supporting transcript evidence

### Risk 4: Product Tries to Do Too Much Too Early
If version 1 attempts full PDD automation, quality and trust will both suffer.

#### Mitigation

- Keep scope centered on `AS-IS`
- Support review-first workflow
- Treat `TO-BE` as a later-phase capability

### Risk 5: Governance Friction Blocks Adoption
Sensitive recordings may trigger internal concerns.

#### Mitigation

- Keep deployment internal
- Limit pilot group
- Design early with retention and access control in mind

### Risk 6: Mixed Recording Quality
Recordings may vary in clarity, pace, cursor visibility, narration quality, and transcript quality.

#### Mitigation

- Make uncertainty visible
- Support BA corrections efficiently
- Build the product promise around first-draft acceleration, not perfect automation

## 14. Recommended Development Phases

### Phase 1: Proof of Value

Goal:
Demonstrate that the system can generate a useful first draft of `AS-IS` from required inputs.

Scope:

- Upload required artifacts
- Analyze video and transcript
- Extract ordered steps
- Generate candidate screenshots
- Show step-review workspace
- Enable moderate editing
- Export editable DOCX

Success Criteria:

- BAs can complete review significantly faster than writing from scratch
- Output is recognizable as a real PDD draft
- Users trust the evidence linkage

### Phase 2: Workflow Hardening

Goal:
Improve reliability, governance, and adoption readiness.

Scope:

- Better confidence handling
- Stronger artifact management
- Improved business-rule extraction
- Better export fidelity
- Identity and access improvements
- Review history and auditability

Success Criteria:

- Consistent internal pilot usage
- Reduced correction volume
- Fewer rejected drafts

### Phase 3: Department Readiness

Goal:
Support broader internal use across more analysts and more process types.

Scope:

- More resilient throughput handling
- Better monitoring and job management
- Template-adjacent enhancements if needed
- Expanded process coverage where justified

Success Criteria:

- Stable throughput across monthly team demand
- Acceptable processing times for longer recordings
- Strong BA satisfaction and repeat usage

### Phase 4: Strategic Expansion

Goal:
Expand from PDD drafting toward broader process intelligence.

Potential Additions:

- Assisted `TO-BE` suggestions
- Better process classification
- Automation opportunity insights
- Structured handoff to development design artifacts
- Partial automation workflow generation support

## 15. Best-Fit Product Positioning

This product should be positioned internally as:

"An AI drafting assistant for Business Analysts that converts discovery evidence into a trustworthy first draft PDD."

It should not be positioned as:

- A fully autonomous document writer
- A replacement for BA judgment
- A generic meeting summarizer

The strength of the product is disciplined process drafting with evidence-backed structure.

## 16. Future Expansion Possibilities

Once the system reliably captures process structure, several logical extensions become possible:

- `TO-BE` suggestion assistance
- Exception-path documentation support
- Better field-level and click-target annotation
- Traceable linkage between business rules and automation logic
- Discovery quality scoring
- Process standardization insights across projects
- Pre-development automation design artifacts
- Foundations for partial RPA workflow generation

## 17. Final Recommendation Summary

### Best Overall Product Shape
An internal, BA-first, human-in-the-loop web application that generates a high-quality first draft of the `AS-IS` PDD from video, transcript, and template inputs.

### Best Workflow Choice
Reviewable structured process extraction with moderate editing before DOCX export.

### Best Scope for Version 1

- Highly structured desktop and web processes
- Single standard template
- Single-user BA workflow
- Confidence-aware drafting
- Internal-only deployment

### Best Strategic Principle
Optimize for trust, traceability, and time saved, not for the illusion of full automation.
