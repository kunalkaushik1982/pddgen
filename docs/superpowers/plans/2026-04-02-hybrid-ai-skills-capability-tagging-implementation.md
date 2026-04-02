# Hybrid AI Skills Capability Tagging Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate workflow capability tagging into a hybrid AI skill while keeping `ProcessGroupingService` responsible for accepted-confidence checks, normalization, and fallback tags.

**Architecture:** Add one new worker-side skill under `worker/services/ai_skills/`: `workflow_capability_tagging`. Keep [process_grouping_service.py](C:/Users/work/Documents/PddGenerator/worker/services/process_grouping_service.py) as the orchestration and fallback layer, but replace its direct call into `AITranscriptInterpreter.classify_workflow_capabilities(...)` with a call into the new skill so only AI request/response behavior moves.

**Tech Stack:** Python, dataclasses, existing AI skill runtime/client helpers, markdown prompts, worker logging, direct-file unittest-style tests

---

## File Structure

### New files

- `worker/services/ai_skills/workflow_capability_tagging/README.md`
- `worker/services/ai_skills/workflow_capability_tagging/prompt.md`
- `worker/services/ai_skills/workflow_capability_tagging/schemas.py`
- `worker/services/ai_skills/workflow_capability_tagging/skill.py`
- `worker/tests/test_workflow_capability_tagging_skill.py`

### Modified files

- `worker/services/ai_skills/registry.py`
- `worker/services/process_grouping_service.py`

### Reference files

- `worker/services/ai_transcript_interpreter.py`
- `worker/services/ai_skills/process_summary_generation/skill.py`
- `worker/services/ai_skills/workflow_group_match/skill.py`

---

### Task 1: Add Workflow Capability Tagging Schemas And Tests

**Files:**
- Create: `worker/services/ai_skills/workflow_capability_tagging/schemas.py`
- Create: `worker/tests/test_workflow_capability_tagging_skill.py`

- [ ] **Step 1: Write the failing schema tests**

```python
from worker.services.ai_skills.workflow_capability_tagging.schemas import (
    WorkflowCapabilityTaggingRequest,
    WorkflowCapabilityTaggingResponse,
)


def test_capability_tagging_request_keeps_workflow_inputs() -> None:
    request = WorkflowCapabilityTaggingRequest(
        process_title="Vendor Creation",
        workflow_summary={"top_goals": ["Create vendor"]},
        document_type="pdd",
    )

    assert request.process_title == "Vendor Creation"
    assert request.document_type == "pdd"


def test_capability_tagging_response_keeps_result_fields() -> None:
    response = WorkflowCapabilityTaggingResponse(
        capability_tags=["Procurement", "Vendor Management"],
        confidence="high",
        rationale="Workflow aligns to procurement capabilities.",
    )

    assert response.capability_tags == ["Procurement", "Vendor Management"]
    assert response.confidence == "high"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python worker\tests\test_workflow_capability_tagging_skill.py`

Expected: FAIL with missing schema module.

- [ ] **Step 3: Write minimal schema models**

```python
from dataclasses import dataclass


@dataclass(slots=True)
class WorkflowCapabilityTaggingRequest:
    process_title: str
    workflow_summary: dict[str, object]
    document_type: str


@dataclass(slots=True)
class WorkflowCapabilityTaggingResponse:
    capability_tags: list[str]
    confidence: str = "unknown"
    rationale: str = ""
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python worker\tests\test_workflow_capability_tagging_skill.py`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add worker/services/ai_skills/workflow_capability_tagging/schemas.py worker/tests/test_workflow_capability_tagging_skill.py
git commit -m "Add workflow capability tagging skill schemas"
```

---

### Task 2: Add Workflow Capability Tagging Markdown Assets

**Files:**
- Create: `worker/services/ai_skills/workflow_capability_tagging/README.md`
- Create: `worker/services/ai_skills/workflow_capability_tagging/prompt.md`

- [ ] **Step 1: Add `README.md`**

Include:
- purpose
- inputs and outputs
- business-capability-versus-workflow-identity rule
- 1 to 3 label constraint
- confidence expectations

- [ ] **Step 2: Add `prompt.md`**

Include:
- strict JSON keys: `capability_tags`, `confidence`, `rationale`
- instruction to return broad reusable business capability labels
- instruction not to return exact workflow titles or tool names
- instruction to stay scoped to one workflow summary

- [ ] **Step 3: Verify files exist**

Run: `Get-ChildItem worker\services\ai_skills\workflow_capability_tagging`

Expected: shows `README.md`, `prompt.md`, `schemas.py`.

- [ ] **Step 4: Commit**

```bash
git add worker/services/ai_skills/workflow_capability_tagging/README.md worker/services/ai_skills/workflow_capability_tagging/prompt.md
git commit -m "Add workflow capability tagging skill markdown assets"
```

---

### Task 3: Implement Workflow Capability Tagging Skill

**Files:**
- Create: `worker/services/ai_skills/workflow_capability_tagging/skill.py`
- Modify: `worker/tests/test_workflow_capability_tagging_skill.py`

- [ ] **Step 1: Write failing tests for normalization and message-building**

Add tests for:
- confidence normalization
- capability-tag de-duplication and process-title exclusion
- `build_messages(...)` containing process title and document type

```python
def test_normalize_confidence_limits_values() -> None:
    assert normalize_confidence("HIGH") == "high"
    assert normalize_confidence("bad") == "medium"


def test_normalize_capability_tags_excludes_process_title() -> None:
    tags = normalize_capability_tags(
        ["Vendor Creation", "Procurement", "procurement", "Vendor Management"],
        process_title="Vendor Creation",
    )

    assert tags == ["Procurement", "Vendor Management"]


def test_build_messages_includes_capability_context() -> None:
    skill = WorkflowCapabilityTaggingSkill(client=object())
    request = WorkflowCapabilityTaggingRequest(
        process_title="Vendor Creation",
        workflow_summary={"top_goals": ["Create vendor"]},
        document_type="pdd",
    )

    messages = skill.build_messages(request)

    assert messages[0]["role"] == "system"
    assert "business capability tags" in messages[0]["content"]
    assert "Vendor Creation" in messages[1]["content"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python worker\tests\test_workflow_capability_tagging_skill.py`

Expected: FAIL with missing `skill.py`.

- [ ] **Step 3: Implement `skill.py`**

The skill should:
- follow the same import fallback pattern as the existing skills
- use the shared AI client/runtime helpers
- normalize the returned capability tag list
- exclude the exact process title from the returned tags
- normalize confidence
- return `WorkflowCapabilityTaggingResponse` even when the tag list is empty, so service-layer fallback policy remains unchanged

- [ ] **Step 4: Run tests to verify they pass**

Run: `python worker\tests\test_workflow_capability_tagging_skill.py`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add worker/services/ai_skills/workflow_capability_tagging/skill.py worker/tests/test_workflow_capability_tagging_skill.py
git commit -m "Implement workflow capability tagging AI skill"
```

---

### Task 4: Wire Workflow Capability Tagging Into Grouping Service

**Files:**
- Modify: `worker/services/process_grouping_service.py`
- Modify: `worker/tests/test_workflow_capability_tagging_skill.py`

- [ ] **Step 1: Write the failing compatibility tests**

Add tests for:
- accepted-confidence AI result wins
- low-confidence AI result falls back to `_fallback_capability_tags(...)`
- empty AI tags fall back to `[process_title]` when fallback tags are empty

```python
def test_grouping_service_uses_capability_skill_when_confident() -> None:
    service = ProcessGroupingService()
    service._workflow_capability_tagging_skill = StubCapabilitySkill(
        capability_tags=["Procurement", "Vendor Management"],
        confidence="high",
    )

    result = service._resolve_capability_tags(
        process_title="Vendor Creation",
        workflow_summary={"top_goals": ["Create vendor"]},
        workflow_profiles=[],
        document_type="pdd",
    )

    assert result == ["Procurement", "Vendor Management"]


def test_grouping_service_falls_back_when_capability_skill_is_weak() -> None:
    service = ProcessGroupingService()
    service._workflow_capability_tagging_skill = StubCapabilitySkill(
        capability_tags=["Procurement"],
        confidence="low",
    )

    result = service._resolve_capability_tags(
        process_title="Vendor Creation",
        workflow_summary={"top_goals": ["Create vendor"]},
        workflow_profiles=[StubWorkflowProfile(top_domain_terms=["supplier onboarding"])],
        document_type="pdd",
    )

    assert result == ["Supplier Onboarding"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python worker\tests\test_workflow_capability_tagging_skill.py`

Expected: FAIL because grouping service still calls the interpreter directly.

- [ ] **Step 3: Update `ProcessGroupingService`**

Implementation notes:
- initialize `self._workflow_capability_tagging_skill` lazily from `build_default_ai_skill_registry()`
- add an INFO log before execution with `skill_id=workflow_capability_tagging`
- preserve the current accepted-confidence behavior
- preserve `_normalize_capability_tags(...)`
- preserve `_fallback_capability_tags(...)`
- preserve `[process_title]` fallback when both AI and workflow-profile fallbacks are empty

- [ ] **Step 4: Run tests to verify they pass**

Run: `python worker\tests\test_workflow_capability_tagging_skill.py`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add worker/services/process_grouping_service.py worker/tests/test_workflow_capability_tagging_skill.py
git commit -m "Wire workflow capability tagging skill into grouping service"
```

---

### Task 5: Register The New Skill

**Files:**
- Modify: `worker/services/ai_skills/registry.py`
- Modify: `worker/tests/test_workflow_capability_tagging_skill.py`

- [ ] **Step 1: Write the failing registry test**

Add a test proving `build_default_ai_skill_registry()` can create `workflow_capability_tagging`.

```python
def test_default_registry_creates_workflow_capability_tagging_skill() -> None:
    registry = build_default_ai_skill_registry()

    assert registry.create("workflow_capability_tagging").skill_id == "workflow_capability_tagging"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python worker\tests\test_workflow_capability_tagging_skill.py`

Expected: FAIL with unknown registry key.

- [ ] **Step 3: Update the registry**

Implementation notes:
- add `_load_workflow_capability_tagging_skill()`
- register it in `build_default_ai_skill_registry()`

- [ ] **Step 4: Run tests to verify they pass**

Run: `python worker\tests\test_workflow_capability_tagging_skill.py`
Run: `python worker\tests\test_ai_skill_runtime.py`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add worker/services/ai_skills/registry.py worker/tests/test_workflow_capability_tagging_skill.py
git commit -m "Register workflow capability tagging AI skill"
```

---

### Task 6: Run Focused Verification And Capture Runtime Proof Expectations

**Files:**
- Modify: `worker/services/process_grouping_service.py` (if additional log fields are needed)

- [ ] **Step 1: Run the focused test suite**

Run: `python worker\tests\test_ai_skill_runtime.py`
Run: `python worker\tests\test_workflow_capability_tagging_skill.py`

Expected: PASS across both files.

- [ ] **Step 2: Verify runtime logging strings are present in code**

Search:

```powershell
rg -n "workflow_capability_tagging|Delegating" worker\services\process_grouping_service.py
```

Expected: log lines include the `workflow_capability_tagging` skill identifier.

- [ ] **Step 3: Commit final verification-only adjustments if needed**

```bash
git add worker/services/process_grouping_service.py worker/tests/test_workflow_capability_tagging_skill.py
git commit -m "Finalize workflow capability tagging AI skill migration"
```

- [ ] **Step 4: Manual runtime verification after worker restart**

Run one new generation and confirm worker logs include:
- `skill_id=workflow_capability_tagging`

Expected: capability-tagging execution is visible during process-group refresh before fallback handling.

---

## Self-Review

### Spec coverage

- new workflow-capability-tagging skill: covered by Tasks 1-3
- registry wiring: covered by Task 5
- grouping-service integration: covered by Task 4
- preserve accepted-confidence and fallback behavior: covered by Task 4
- focused tests: covered by Tasks 1, 3, 4, 5, and 6
- runtime logs: covered by Tasks 4 and 6

### Placeholder scan

- no `TODO`, `TBD`, or “implement later” placeholders remain
- every code-changing task names exact files
- every validation task includes explicit commands and expected outcomes

### Type consistency

- request/response types use `WorkflowCapabilityTaggingRequest/Response`
- grouping service still owns acceptance and fallback policy
- registry key matches the planned skill folder name
