# Hybrid AI Skills Group Resolution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate workflow title resolution and existing-group matching into hybrid AI skills while keeping `ProcessGroupingService` as the orchestration, heuristic, and conflict-resolution layer.

**Architecture:** Add two new worker-side skills under `worker/services/ai_skills/`: `workflow_title_resolution` and `workflow_group_match`. Keep [process_grouping_service.py](C:/Users/work/Documents/PddGenerator/worker/services/process_grouping_service.py) responsible for building workflow summaries, choosing fallbacks, and resolving heuristic-versus-AI conflicts, but replace its direct AI interpreter calls with calls into the new skills.

**Tech Stack:** Python, dataclasses, existing AI skill runtime/client helpers, markdown prompts, worker logging, direct-file unittest-style tests

---

## File Structure

### New files

- `worker/services/ai_skills/workflow_title_resolution/SKILL.md`
- `worker/services/ai_skills/workflow_title_resolution/prompt.md`
- `worker/services/ai_skills/workflow_title_resolution/schemas.py`
- `worker/services/ai_skills/workflow_title_resolution/skill.py`
- `worker/services/ai_skills/workflow_group_match/SKILL.md`
- `worker/services/ai_skills/workflow_group_match/prompt.md`
- `worker/services/ai_skills/workflow_group_match/schemas.py`
- `worker/services/ai_skills/workflow_group_match/skill.py`
- `worker/tests/test_workflow_title_resolution_skill.py`
- `worker/tests/test_workflow_group_match_skill.py`

### Modified files

- `worker/services/ai_skills/registry.py`
- `worker/services/process_grouping_service.py`

### Reference files

- `worker/services/ai_transcript_interpreter.py`
- `worker/services/ai_skills/transcript_to_steps/skill.py`
- `worker/services/ai_skills/semantic_enrichment/skill.py`
- `worker/services/ai_skills/workflow_boundary_detection/skill.py`

---

### Task 1: Add Workflow Title Resolution Schemas And Tests

**Files:**
- Create: `worker/services/ai_skills/workflow_title_resolution/schemas.py`
- Create: `worker/tests/test_workflow_title_resolution_skill.py`

- [ ] **Step 1: Write the failing schema tests**

```python
from worker.services.ai_skills.workflow_title_resolution.schemas import (
    WorkflowTitleResolutionRequest,
    WorkflowTitleResolutionResponse,
)


def test_workflow_title_resolution_request_keeps_summary() -> None:
    request = WorkflowTitleResolutionRequest(
        transcript_name="artifact-1",
        workflow_summary={"top_goals": ["Create Vendor"], "top_systems": ["SAP"]},
    )

    assert request.transcript_name == "artifact-1"
    assert request.workflow_summary["top_goals"] == ["Create Vendor"]


def test_workflow_title_resolution_response_keeps_title_and_slug() -> None:
    response = WorkflowTitleResolutionResponse(
        workflow_title="Vendor Creation",
        canonical_slug="vendor-creation",
        confidence="high",
        rationale="Repeated vendor creation evidence",
    )

    assert response.workflow_title == "Vendor Creation"
    assert response.canonical_slug == "vendor-creation"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python worker\tests\test_workflow_title_resolution_skill.py`

Expected: FAIL with missing schema module.

- [ ] **Step 3: Write minimal schema models**

```python
@dataclass(slots=True)
class WorkflowTitleResolutionRequest:
    transcript_name: str
    workflow_summary: dict[str, object]


@dataclass(slots=True)
class WorkflowTitleResolutionResponse:
    workflow_title: str
    canonical_slug: str
    confidence: str = "unknown"
    rationale: str = ""
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python worker\tests\test_workflow_title_resolution_skill.py`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add worker/services/ai_skills/workflow_title_resolution/schemas.py worker/tests/test_workflow_title_resolution_skill.py
git commit -m "Add workflow title resolution skill schemas"
```

---

### Task 2: Add Workflow Title Resolution Markdown Assets

**Files:**
- Create: `worker/services/ai_skills/workflow_title_resolution/SKILL.md`
- Create: `worker/services/ai_skills/workflow_title_resolution/prompt.md`

- [ ] **Step 1: Add `SKILL.md`**

Include:
- purpose
- input/output contract
- title-quality rules
- slug expectations
- confidence rules

- [ ] **Step 2: Add `prompt.md`**

Include:
- instruction to prefer operational workflow identity over UI phrasing
- strict JSON keys: `workflow_title`, `canonical_slug`, `confidence`, `rationale`
- guidance against broad labels like domain-only names
- lower-confidence guidance for weak evidence

- [ ] **Step 3: Verify files exist**

Run: `Get-ChildItem worker\services\ai_skills\workflow_title_resolution`

Expected: shows `SKILL.md`, `prompt.md`, `schemas.py`.

- [ ] **Step 4: Commit**

```bash
git add worker/services/ai_skills/workflow_title_resolution/SKILL.md worker/services/ai_skills/workflow_title_resolution/prompt.md
git commit -m "Add workflow title resolution skill markdown assets"
```

---

### Task 3: Implement Workflow Title Resolution Skill

**Files:**
- Create: `worker/services/ai_skills/workflow_title_resolution/skill.py`
- Modify: `worker/tests/test_workflow_title_resolution_skill.py`

- [ ] **Step 1: Write failing tests for normalization and message-building**

Add tests for:
- confidence normalization
- title cleanup
- slug fallback normalization
- `build_messages(...)` containing prompt content and workflow summary

```python
def test_normalize_confidence_limits_values() -> None:
    assert normalize_confidence("HIGH") == "high"
    assert normalize_confidence("unexpected") == "medium"


def test_build_messages_includes_workflow_summary() -> None:
    skill = WorkflowTitleResolutionSkill(client=object())
    request = WorkflowTitleResolutionRequest(
        transcript_name="artifact-1",
        workflow_summary={"top_goals": ["Create Vendor"]},
    )

    messages = skill.build_messages(request)

    assert messages[0]["role"] == "system"
    assert "business workflow title" in messages[0]["content"]
    assert "Create Vendor" in messages[1]["content"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python worker\tests\test_workflow_title_resolution_skill.py`

Expected: FAIL with missing `skill.py`.

- [ ] **Step 3: Implement `skill.py`**

The skill should:
- follow the same import fallback pattern as the existing skills
- use the shared AI client/runtime helpers
- normalize blank or invalid titles to `None`
- normalize `canonical_slug` with title fallback
- normalize confidence
- return `WorkflowTitleResolutionResponse | None`

- [ ] **Step 4: Run tests to verify they pass**

Run: `python worker\tests\test_workflow_title_resolution_skill.py`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add worker/services/ai_skills/workflow_title_resolution/skill.py worker/tests/test_workflow_title_resolution_skill.py
git commit -m "Implement workflow title resolution AI skill"
```

---

### Task 4: Wire Process Grouping Title Resolution To The New Skill

**Files:**
- Modify: `worker/services/process_grouping_service.py`
- Modify: `worker/tests/test_workflow_title_resolution_skill.py`

- [ ] **Step 1: Write the failing compatibility test**

Test that `ProcessGroupingService._resolve_title_with_ai(...)`:
- still builds the fallback title
- uses a stub skill result when AI confidence is accepted
- still returns `WorkflowTitleInterpretation`

```python
def test_process_grouping_title_resolution_uses_skill_and_preserves_dataclass() -> None:
    service = ProcessGroupingService()
    service._workflow_title_resolution_skill = StubWorkflowTitleSkill(
        workflow_title="Vendor Creation",
        canonical_slug="vendor-creation",
        confidence="high",
    )

    result = service._resolve_title_with_ai(
        transcript=StubArtifact(name="artifact-1"),
        steps=[{"title": "Create vendor"}],
        workflow_profile=StubWorkflowProfile(),
        fallback_title="Fallback Title",
    )

    assert isinstance(result, WorkflowTitleInterpretation)
    assert result.workflow_title == "Vendor Creation"
    assert result.canonical_slug == "vendor-creation"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python worker\tests\test_workflow_title_resolution_skill.py`

Expected: FAIL because `ProcessGroupingService` still calls the interpreter directly.

- [ ] **Step 3: Update `ProcessGroupingService`**

Implementation notes:
- initialize `self._workflow_title_resolution_skill` lazily from `build_default_ai_skill_registry()`
- add an INFO log before execution with `skill_id=workflow_title_resolution`
- keep `fallback_title` behavior unchanged when AI result is missing or low confidence
- keep returning `WorkflowTitleInterpretation`

- [ ] **Step 4: Run tests to verify they pass**

Run: `python worker\tests\test_workflow_title_resolution_skill.py`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add worker/services/process_grouping_service.py worker/tests/test_workflow_title_resolution_skill.py
git commit -m "Wire workflow title resolution skill into grouping service"
```

---

### Task 5: Add Workflow Group Match Schemas And Tests

**Files:**
- Create: `worker/services/ai_skills/workflow_group_match/schemas.py`
- Create: `worker/tests/test_workflow_group_match_skill.py`

- [ ] **Step 1: Write the failing schema tests**

```python
from worker.services.ai_skills.workflow_group_match.schemas import (
    WorkflowGroupMatchRequest,
    WorkflowGroupMatchResponse,
)


def test_workflow_group_match_request_keeps_existing_groups() -> None:
    request = WorkflowGroupMatchRequest(
        transcript_name="artifact-1",
        workflow_summary={"top_systems": ["SAP"]},
        existing_groups=[{"title": "Vendor Creation"}],
    )

    assert request.transcript_name == "artifact-1"
    assert request.existing_groups[0]["title"] == "Vendor Creation"


def test_workflow_group_match_response_keeps_match_fields() -> None:
    response = WorkflowGroupMatchResponse(
        matched_existing_title="Vendor Creation",
        recommended_title="Vendor Creation",
        recommended_slug="vendor-creation",
        confidence="high",
        rationale="Same system and outcome",
    )

    assert response.matched_existing_title == "Vendor Creation"
    assert response.recommended_slug == "vendor-creation"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python worker\tests\test_workflow_group_match_skill.py`

Expected: FAIL with missing schema module.

- [ ] **Step 3: Write minimal schema models**

```python
@dataclass(slots=True)
class WorkflowGroupMatchRequest:
    transcript_name: str
    workflow_summary: dict[str, object]
    existing_groups: list[dict[str, object]]


@dataclass(slots=True)
class WorkflowGroupMatchResponse:
    matched_existing_title: str | None = None
    recommended_title: str = ""
    recommended_slug: str = ""
    confidence: str = "unknown"
    rationale: str = ""
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python worker\tests\test_workflow_group_match_skill.py`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add worker/services/ai_skills/workflow_group_match/schemas.py worker/tests/test_workflow_group_match_skill.py
git commit -m "Add workflow group match skill schemas"
```

---

### Task 6: Add Workflow Group Match Markdown Assets

**Files:**
- Create: `worker/services/ai_skills/workflow_group_match/SKILL.md`
- Create: `worker/services/ai_skills/workflow_group_match/prompt.md`

- [ ] **Step 1: Add `SKILL.md`**

Include:
- purpose
- inputs/outputs
- rules for matching only materially same workflows
- rules against domain-only grouping
- confidence expectations

- [ ] **Step 2: Add `prompt.md`**

Include:
- strict JSON keys: `matched_existing_title`, `recommended_title`, `recommended_slug`, `confidence`, `rationale`
- instruction that `matched_existing_title` must be one exact existing title or empty
- instruction to prefer a new group when only broad domain overlap exists
- slug normalization expectations

- [ ] **Step 3: Verify files exist**

Run: `Get-ChildItem worker\services\ai_skills\workflow_group_match`

Expected: shows `SKILL.md`, `prompt.md`, `schemas.py`.

- [ ] **Step 4: Commit**

```bash
git add worker/services/ai_skills/workflow_group_match/SKILL.md worker/services/ai_skills/workflow_group_match/prompt.md
git commit -m "Add workflow group match skill markdown assets"
```

---

### Task 7: Implement Workflow Group Match Skill

**Files:**
- Create: `worker/services/ai_skills/workflow_group_match/skill.py`
- Modify: `worker/tests/test_workflow_group_match_skill.py`

- [ ] **Step 1: Write failing tests for normalization and exact-title matching**

Add tests for:
- confidence normalization
- matching only exact existing titles
- title and slug fallback normalization
- `build_messages(...)` including existing-group payload

```python
def test_group_match_rejects_non_exact_existing_title() -> None:
    request = WorkflowGroupMatchRequest(
        transcript_name="artifact-1",
        workflow_summary={"top_systems": ["SAP"]},
        existing_groups=[{"title": "Vendor Creation"}],
    )
    skill = WorkflowGroupMatchSkill(client=StubClient({"matched_existing_title": "vendor creation"}))

    result = skill.run(request)

    assert result.matched_existing_title is None


def test_build_messages_includes_existing_groups() -> None:
    skill = WorkflowGroupMatchSkill(client=object())
    request = WorkflowGroupMatchRequest(
        transcript_name="artifact-1",
        workflow_summary={"top_systems": ["SAP"]},
        existing_groups=[{"title": "Vendor Creation"}],
    )

    messages = skill.build_messages(request)

    assert "existing_group_titles" in messages[1]["content"]
    assert "Vendor Creation" in messages[1]["content"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python worker\tests\test_workflow_group_match_skill.py`

Expected: FAIL with missing `skill.py`.

- [ ] **Step 3: Implement `skill.py`**

The skill should:
- follow the same import fallback pattern as the existing skills
- use the shared AI client/runtime helpers
- only accept `matched_existing_title` when it exactly matches one serialized group title
- normalize `recommended_title`
- normalize `recommended_slug` with title fallback
- normalize confidence
- return `WorkflowGroupMatchResponse`

- [ ] **Step 4: Run tests to verify they pass**

Run: `python worker\tests\test_workflow_group_match_skill.py`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add worker/services/ai_skills/workflow_group_match/skill.py worker/tests/test_workflow_group_match_skill.py
git commit -m "Implement workflow group match AI skill"
```

---

### Task 8: Wire Process Grouping Match Resolution To The New Skill

**Files:**
- Modify: `worker/services/process_grouping_service.py`
- Modify: `worker/tests/test_workflow_group_match_skill.py`

- [ ] **Step 1: Write the failing compatibility test**

Test that `ProcessGroupingService._match_existing_group_with_ai(...)`:
- still returns `None` when no existing groups exist
- uses a stub skill result when AI returns an accepted match
- preserves `GroupResolutionDecision` conflict logic inputs

```python
def test_process_grouping_group_match_uses_skill() -> None:
    service = ProcessGroupingService()
    service._workflow_group_match_skill = StubWorkflowGroupMatchSkill(
        matched_existing_title="Vendor Creation",
        recommended_title="Vendor Creation",
        recommended_slug="vendor-creation",
        confidence="high",
    )

    result = service._match_existing_group_with_ai(
        transcript=StubArtifact(name="artifact-1"),
        title_resolution=WorkflowTitleInterpretation(
            workflow_title="Vendor Creation",
            canonical_slug="vendor-creation",
            confidence="high",
            rationale="",
        ),
        workflow_profile=StubWorkflowProfile(),
        steps=[],
        notes=[],
        existing_groups=[StubProcessGroup(title="Vendor Creation", canonical_slug="vendor-creation")],
        heuristic_match=stub_heuristic_match(),
    )

    assert isinstance(result, GroupResolutionDecision)
    assert result.ai_decision == "matched_existing_group"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python worker\tests\test_workflow_group_match_skill.py`

Expected: FAIL because `ProcessGroupingService` still calls the interpreter directly.

- [ ] **Step 3: Update `ProcessGroupingService`**

Implementation notes:
- initialize `self._workflow_group_match_skill` lazily from `build_default_ai_skill_registry()`
- add an INFO log before execution with `skill_id=workflow_group_match`
- preserve exact heuristic-vs-AI conflict logic already in `_match_existing_group_with_ai(...)`
- preserve `None` return when the skill returns no usable result

- [ ] **Step 4: Run tests to verify they pass**

Run: `python worker\tests\test_workflow_group_match_skill.py`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add worker/services/process_grouping_service.py worker/tests/test_workflow_group_match_skill.py
git commit -m "Wire workflow group match skill into grouping service"
```

---

### Task 9: Register The New Skills

**Files:**
- Modify: `worker/services/ai_skills/registry.py`
- Modify: `worker/tests/test_workflow_title_resolution_skill.py`
- Modify: `worker/tests/test_workflow_group_match_skill.py`

- [ ] **Step 1: Write failing registry tests**

Add tests proving `build_default_ai_skill_registry()` can create:
- `workflow_title_resolution`
- `workflow_group_match`

```python
def test_default_registry_creates_group_resolution_skills() -> None:
    registry = build_default_ai_skill_registry()

    assert registry.create("workflow_title_resolution").skill_id == "workflow_title_resolution"
    assert registry.create("workflow_group_match").skill_id == "workflow_group_match"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python worker\tests\test_workflow_title_resolution_skill.py`

Expected: FAIL with unknown registry keys.

- [ ] **Step 3: Update the registry**

Implementation notes:
- add `_load_workflow_title_resolution_skill()`
- add `_load_workflow_group_match_skill()`
- register both in `build_default_ai_skill_registry()`

- [ ] **Step 4: Run tests to verify they pass**

Run: `python worker\tests\test_workflow_title_resolution_skill.py`
Run: `python worker\tests\test_workflow_group_match_skill.py`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add worker/services/ai_skills/registry.py worker/tests/test_workflow_title_resolution_skill.py worker/tests/test_workflow_group_match_skill.py
git commit -m "Register workflow group resolution skills"
```

---

### Task 10: Run Focused Verification And Capture Runtime Proof Expectations

**Files:**
- Modify: `worker/services/process_grouping_service.py` (if additional log fields are needed)

- [ ] **Step 1: Run the focused test suite**

Run: `python worker\tests\test_ai_skill_runtime.py`
Run: `python worker\tests\test_workflow_title_resolution_skill.py`
Run: `python worker\tests\test_workflow_group_match_skill.py`

Expected: PASS across all three files.

- [ ] **Step 2: Verify runtime logging strings are present in code**

Search:

```powershell
rg -n "workflow_title_resolution|workflow_group_match|Delegating workflow" worker\services\process_grouping_service.py
```

Expected: log lines include both skill identifiers.

- [ ] **Step 3: Commit final verification-only adjustments if needed**

```bash
git add worker/services/process_grouping_service.py worker/tests/test_workflow_title_resolution_skill.py worker/tests/test_workflow_group_match_skill.py
git commit -m "Finalize workflow group resolution skill migration"
```

- [ ] **Step 4: Manual runtime verification after worker restart**

Run one new generation and confirm worker logs include:
- `skill_id=workflow_title_resolution`
- `skill_id=workflow_group_match`

Expected: real grouping flow shows both AI skill paths before title/group decision handling.

---

## Self-Review

### Spec coverage

- new title-resolution skill: covered by Tasks 1-4
- new group-match skill: covered by Tasks 5-8
- registry wiring: covered by Task 9
- focused tests: covered by Tasks 1, 3, 5, 7, 9, and 10
- runtime logs: covered by Tasks 4, 8, and 10
- keep `ProcessGroupingService` as orchestration layer: covered by Tasks 4 and 8
- preserve heuristic/conflict logic: covered by Task 8

### Placeholder scan

- no `TODO`, `TBD`, or “implement later” placeholders remain
- every code-changing task names exact files
- every validation task includes explicit commands and expected outcomes

### Type consistency

- request/response types use `WorkflowTitleResolutionRequest/Response` and `WorkflowGroupMatchRequest/Response`
- service compatibility steps continue returning `WorkflowTitleInterpretation` and `GroupResolutionDecision`
- registry keys match the planned skill folder names
