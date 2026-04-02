# Hybrid AI Skills Workflow Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate workflow semantic enrichment and workflow-boundary detection into hybrid AI skills while keeping the current evidence-segmentation strategies, heuristic fallbacks, and downstream dataclass shapes stable.

**Architecture:** Add two new worker-side skills under `worker/services/ai_skills/`: `semantic_enrichment` and `workflow_boundary_detection`. Keep `worker/services/evidence_segmentation_service.py` as the orchestration and fallback layer, but replace its direct calls into `AITranscriptInterpreter` with calls into the new skills; preserve the current fallback and conflict-resolution behavior.

**Tech Stack:** Python, dataclasses, existing AI skill runtime/client helpers, unittest-style focused test files, markdown prompts, worker logging

---

## File Structure

### New files

- `worker/services/ai_skills/semantic_enrichment/SKILL.md`
- `worker/services/ai_skills/semantic_enrichment/prompt.md`
- `worker/services/ai_skills/semantic_enrichment/schemas.py`
- `worker/services/ai_skills/semantic_enrichment/skill.py`
- `worker/services/ai_skills/workflow_boundary_detection/SKILL.md`
- `worker/services/ai_skills/workflow_boundary_detection/prompt.md`
- `worker/services/ai_skills/workflow_boundary_detection/schemas.py`
- `worker/services/ai_skills/workflow_boundary_detection/skill.py`
- `worker/tests/test_semantic_enrichment_skill.py`
- `worker/tests/test_workflow_boundary_detection_skill.py`

### Modified files

- `worker/services/ai_skills/registry.py`
- `worker/services/evidence_segmentation_service.py`
- `worker/services/ai_transcript_interpreter.py`

### Reference files

- `worker/services/workflow_intelligence.py`
- `worker/services/workflow_strategy_interfaces.py`
- `worker/services/ai_skills/transcript_to_steps/skill.py`

---

### Task 1: Add Semantic Enrichment Schemas And Tests

**Files:**
- Create: `worker/services/ai_skills/semantic_enrichment/schemas.py`
- Create: `worker/tests/test_semantic_enrichment_skill.py`

- [ ] **Step 1: Write the failing schema tests**

```python
from worker.services.ai_skills.semantic_enrichment.schemas import (
    SemanticEnrichmentRequest,
    SemanticEnrichmentResponse,
)


def test_semantic_enrichment_request_keeps_segment_context() -> None:
    request = SemanticEnrichmentRequest(
        transcript_name="artifact-1",
        segment_text="Open SAP and review the vendor record",
        segment_context={"segment_order": 1, "start_timestamp": "00:00:05"},
    )

    assert request.transcript_name == "artifact-1"
    assert request.segment_context["segment_order"] == 1


def test_semantic_enrichment_response_keeps_labels() -> None:
    response = SemanticEnrichmentResponse(
        actor="User",
        actor_role="operator",
        system_name="SAP",
        action_verb="review",
        action_type="review",
        business_object="Vendor",
        workflow_goal="Review Vendor",
        rule_hints=["Validate before submit"],
        domain_terms=["vendor", "review"],
        confidence="high",
        rationale="Direct UI and object evidence",
    )

    assert response.system_name == "SAP"
    assert response.confidence == "high"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python worker\tests\test_semantic_enrichment_skill.py`

Expected: FAIL with missing schema module.

- [ ] **Step 3: Write minimal schema models**

```python
@dataclass(slots=True)
class SemanticEnrichmentRequest:
    transcript_name: str
    segment_text: str
    segment_context: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class SemanticEnrichmentResponse:
    actor: str | None = None
    actor_role: str | None = None
    system_name: str | None = None
    action_verb: str | None = None
    action_type: str | None = None
    business_object: str | None = None
    workflow_goal: str | None = None
    rule_hints: list[str] = field(default_factory=list)
    domain_terms: list[str] = field(default_factory=list)
    confidence: str = "unknown"
    rationale: str = ""
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python worker\tests\test_semantic_enrichment_skill.py`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add worker/services/ai_skills/semantic_enrichment/schemas.py worker/tests/test_semantic_enrichment_skill.py
git commit -m "Add semantic enrichment skill schemas"
```

---

### Task 2: Add Semantic Enrichment Markdown Assets

**Files:**
- Create: `worker/services/ai_skills/semantic_enrichment/SKILL.md`
- Create: `worker/services/ai_skills/semantic_enrichment/prompt.md`

- [ ] **Step 1: Add `SKILL.md`**

Include:
- purpose
- inputs
- outputs
- rules against over-inference
- allowed confidence values

- [ ] **Step 2: Add `prompt.md`**

Include:
- system instruction for one segment
- strict JSON output keys
- null-handling for unknown fields
- array rules for `rule_hints` and `domain_terms`

- [ ] **Step 3: Verify files exist**

Run: `Get-ChildItem worker\services\ai_skills\semantic_enrichment`

Expected: shows `SKILL.md`, `prompt.md`, `schemas.py`.

- [ ] **Step 4: Commit**

```bash
git add worker/services/ai_skills/semantic_enrichment/SKILL.md worker/services/ai_skills/semantic_enrichment/prompt.md
git commit -m "Add semantic enrichment skill markdown assets"
```

---

### Task 3: Implement Semantic Enrichment Skill

**Files:**
- Create: `worker/services/ai_skills/semantic_enrichment/skill.py`
- Modify: `worker/tests/test_semantic_enrichment_skill.py`

- [ ] **Step 1: Write failing tests for normalization and prompt building**

Add tests for:
- confidence normalization
- list normalization
- `build_messages(...)` including prompt + segment text

```python
def test_normalize_confidence_limits_values() -> None:
    assert normalize_confidence("HIGH") == "high"
    assert normalize_confidence("bad") == "medium"


def test_build_messages_includes_segment_text() -> None:
    skill = SemanticEnrichmentSkill(client=object())
    request = SemanticEnrichmentRequest(
        transcript_name="artifact-1",
        segment_text="Open SAP and review vendor",
        segment_context={"segment_order": 1},
    )

    messages = skill.build_messages(request)

    assert messages[0]["role"] == "system"
    assert "workflow evidence segment" in messages[0]["content"]
    assert "Open SAP and review vendor" in messages[1]["content"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python worker\tests\test_semantic_enrichment_skill.py`

Expected: FAIL with missing `skill.py`.

- [ ] **Step 3: Implement `skill.py`**

The skill should:
- follow the same import/fallback pattern as `transcript_to_steps`
- use the shared AI client/runtime helpers
- normalize confidence
- normalize `rule_hints` and `domain_terms` to bounded unique lists
- return `SemanticEnrichmentResponse`

- [ ] **Step 4: Run tests to verify they pass**

Run: `python worker\tests\test_semantic_enrichment_skill.py`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add worker/services/ai_skills/semantic_enrichment/skill.py worker/tests/test_semantic_enrichment_skill.py
git commit -m "Implement semantic enrichment AI skill"
```

---

### Task 4: Wire Semantic Enrichment Strategy To The New Skill

**Files:**
- Modify: `worker/services/evidence_segmentation_service.py`
- Modify: `worker/tests/test_semantic_enrichment_skill.py`

- [ ] **Step 1: Write the failing compatibility test**

Test that `AISemanticEnrichmentStrategy.enrich(...)`:
- still computes fallback enrichment
- uses a stub skill result when AI is strong
- still returns `SemanticEnrichment`

```python
def test_ai_semantic_strategy_uses_skill_and_preserves_dataclass_shape() -> None:
    strategy = AISemanticEnrichmentStrategy()
    strategy._semantic_enrichment_skill = StubSemanticSkill(...)

    result = strategy.enrich(segment)

    assert isinstance(result, SemanticEnrichment)
    assert result.system_name == "SAP"
    assert result.enrichment_source == "ai"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python worker\tests\test_semantic_enrichment_skill.py`

Expected: FAIL because the strategy still calls `AITranscriptInterpreter.enrich_workflow_segment(...)`.

- [ ] **Step 3: Update `AISemanticEnrichmentStrategy`**

Change it to:
- create `self._semantic_enrichment_skill`
- call that skill instead of `ai_transcript_interpreter.enrich_workflow_segment(...)`
- keep existing fallback merge semantics
- add log line before delegation

- [ ] **Step 4: Run tests to verify they pass**

Run: `python worker\tests\test_semantic_enrichment_skill.py`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add worker/services/evidence_segmentation_service.py worker/tests/test_semantic_enrichment_skill.py
git commit -m "Wire semantic enrichment strategy to AI skill"
```

---

### Task 5: Add Workflow Boundary Detection Schemas And Tests

**Files:**
- Create: `worker/services/ai_skills/workflow_boundary_detection/schemas.py`
- Create: `worker/tests/test_workflow_boundary_detection_skill.py`

- [ ] **Step 1: Write the failing schema tests**

```python
from worker.services.ai_skills.workflow_boundary_detection.schemas import (
    WorkflowBoundaryDetectionRequest,
    WorkflowBoundaryDetectionResponse,
)


def test_boundary_request_keeps_left_and_right_segments() -> None:
    request = WorkflowBoundaryDetectionRequest(
        left_segment={"id": "left-1", "text": "Open SAP"},
        right_segment={"id": "right-1", "text": "Review vendor"},
    )

    assert request.left_segment["id"] == "left-1"
    assert request.right_segment["id"] == "right-1"


def test_boundary_response_keeps_decision_and_confidence() -> None:
    response = WorkflowBoundaryDetectionResponse(
        decision="same_workflow",
        confidence="high",
        rationale="Shared object and system",
    )

    assert response.decision == "same_workflow"
    assert response.confidence == "high"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python worker\tests\test_workflow_boundary_detection_skill.py`

Expected: FAIL with missing schema module.

- [ ] **Step 3: Write minimal schema models**

```python
@dataclass(slots=True)
class WorkflowBoundaryDetectionRequest:
    left_segment: dict[str, object]
    right_segment: dict[str, object]


@dataclass(slots=True)
class WorkflowBoundaryDetectionResponse:
    decision: str
    confidence: str
    rationale: str
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python worker\tests\test_workflow_boundary_detection_skill.py`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add worker/services/ai_skills/workflow_boundary_detection/schemas.py worker/tests/test_workflow_boundary_detection_skill.py
git commit -m "Add workflow boundary detection skill schemas"
```

---

### Task 6: Add Workflow Boundary Detection Markdown Assets

**Files:**
- Create: `worker/services/ai_skills/workflow_boundary_detection/SKILL.md`
- Create: `worker/services/ai_skills/workflow_boundary_detection/prompt.md`

- [ ] **Step 1: Add `SKILL.md`**

Describe:
- adjacent segment continuity purpose
- allowed outputs
- rules for `same_workflow`, `new_workflow`, `uncertain`

- [ ] **Step 2: Add `prompt.md`**

Include:
- strict JSON keys
- decision enum
- confidence enum
- rationale requirement

- [ ] **Step 3: Verify files exist**

Run: `Get-ChildItem worker\services\ai_skills\workflow_boundary_detection`

Expected: shows `SKILL.md`, `prompt.md`, `schemas.py`.

- [ ] **Step 4: Commit**

```bash
git add worker/services/ai_skills/workflow_boundary_detection/SKILL.md worker/services/ai_skills/workflow_boundary_detection/prompt.md
git commit -m "Add workflow boundary detection skill markdown assets"
```

---

### Task 7: Implement Workflow Boundary Detection Skill

**Files:**
- Create: `worker/services/ai_skills/workflow_boundary_detection/skill.py`
- Modify: `worker/tests/test_workflow_boundary_detection_skill.py`

- [ ] **Step 1: Write failing tests for normalization and prompt building**

Add tests for:
- decision normalization
- confidence normalization
- prompt building with both segments

```python
def test_normalize_decision_limits_values() -> None:
    assert normalize_decision("same_workflow") == "same_workflow"
    assert normalize_decision("bad") == "uncertain"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python worker\tests\test_workflow_boundary_detection_skill.py`

Expected: FAIL with missing `skill.py`.

- [ ] **Step 3: Implement `skill.py`**

The skill should:
- use shared client/runtime helpers
- normalize decision to `same_workflow | new_workflow | uncertain`
- normalize confidence
- return `WorkflowBoundaryDetectionResponse`
- log execution with `skill_id` and segment ids where available

- [ ] **Step 4: Run tests to verify they pass**

Run: `python worker\tests\test_workflow_boundary_detection_skill.py`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add worker/services/ai_skills/workflow_boundary_detection/skill.py worker/tests/test_workflow_boundary_detection_skill.py
git commit -m "Implement workflow boundary detection AI skill"
```

---

### Task 8: Wire Workflow Boundary Strategy To The New Skill

**Files:**
- Modify: `worker/services/evidence_segmentation_service.py`
- Modify: `worker/tests/test_workflow_boundary_detection_skill.py`

- [ ] **Step 1: Write the failing compatibility test**

Test that `AIWorkflowBoundaryStrategy.decide(...)`:
- still computes heuristic fallback first
- uses a stub skill result when AI is strong
- preserves the current `WorkflowBoundaryDecision` shape and conflict-resolution behavior

- [ ] **Step 2: Run test to verify it fails**

Run: `python worker\tests\test_workflow_boundary_detection_skill.py`

Expected: FAIL because the strategy still calls `AITranscriptInterpreter.classify_workflow_boundary(...)`.

- [ ] **Step 3: Update `AIWorkflowBoundaryStrategy`**

Change it to:
- create `self._workflow_boundary_skill`
- call that skill instead of `ai_transcript_interpreter.classify_workflow_boundary(...)`
- keep current low-confidence fallback behavior
- keep current conflict-resolution logic
- add strategy-level delegation logging

- [ ] **Step 4: Run tests to verify they pass**

Run: `python worker\tests\test_workflow_boundary_detection_skill.py`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add worker/services/evidence_segmentation_service.py worker/tests/test_workflow_boundary_detection_skill.py
git commit -m "Wire workflow boundary strategy to AI skill"
```

---

### Task 9: Register The New Skills

**Files:**
- Modify: `worker/services/ai_skills/registry.py`
- Modify: `worker/tests/test_ai_skill_runtime.py`

- [ ] **Step 1: Add failing registration tests**

Add assertions that `build_default_ai_skill_registry()` can resolve:
- `semantic_enrichment`
- `workflow_boundary_detection`

- [ ] **Step 2: Run runtime tests to verify failure**

Run: `python worker\tests\test_ai_skill_runtime.py`

Expected: FAIL because those keys are not registered.

- [ ] **Step 3: Update the registry**

Register:
- `semantic_enrichment`
- `workflow_boundary_detection`

Use the same import/fallback style currently used for `transcript_to_steps`.

- [ ] **Step 4: Run runtime tests to verify they pass**

Run: `python worker\tests\test_ai_skill_runtime.py`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add worker/services/ai_skills/registry.py worker/tests/test_ai_skill_runtime.py
git commit -m "Register workflow core AI skills"
```

---

### Task 10: Verification And Runtime Proof

**Files:**
- Test: `worker/tests/test_ai_skill_runtime.py`
- Test: `worker/tests/test_semantic_enrichment_skill.py`
- Test: `worker/tests/test_workflow_boundary_detection_skill.py`
- Verify: worker runtime logs from one real generation run

- [ ] **Step 1: Run focused test files**

Run:
- `python worker\tests\test_ai_skill_runtime.py`
- `python worker\tests\test_semantic_enrichment_skill.py`
- `python worker\tests\test_workflow_boundary_detection_skill.py`

Expected: all PASS.

- [ ] **Step 2: Run one real worker-backed generation after restarting the worker**

Expected worker logs to include:
- semantic enrichment delegation/execution
- workflow boundary detection delegation/execution
- `skill_id`
- `skill_version`

- [ ] **Step 3: Confirm current branch state**

Run: `git status --short --branch`

Expected: clean tracked working tree.

- [ ] **Step 4: Commit final cleanup if needed**

```bash
git add worker/services/ai_skills worker/services/evidence_segmentation_service.py worker/tests
git commit -m "Complete workflow core AI skill migration"
```

---

## Self-Review

### Spec coverage

- semantic enrichment skill:
  - covered by Tasks 1 to 4
- workflow-boundary skill:
  - covered by Tasks 5 to 8
- registry wiring:
  - covered by Task 9
- runtime proof logging:
  - covered by Tasks 4, 8, and 10
- compatibility preservation:
  - covered by Tasks 4 and 8

### Placeholder scan

The plan includes:
- exact files
- concrete test targets
- explicit commands
- implementation boundaries

No `TODO`, `TBD`, or deferred placeholders remain.

### Type consistency

The plan consistently uses:
- `SemanticEnrichmentRequest`
- `SemanticEnrichmentResponse`
- `WorkflowBoundaryDetectionRequest`
- `WorkflowBoundaryDetectionResponse`
- `SemanticEnrichmentSkill`
- `WorkflowBoundaryDetectionSkill`

These names should be used consistently during implementation.
