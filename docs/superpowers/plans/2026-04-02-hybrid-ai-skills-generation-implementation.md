# Hybrid AI Skills Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate process summary generation and diagram generation into hybrid AI skills while keeping `ProcessGroupingService` and `DiagramAssemblyStage` as the orchestration and fallback layers.

**Architecture:** Add two new worker-side skills under `worker/services/ai_skills/`: `process_summary_generation` and `diagram_generation`. Keep [process_grouping_service.py](C:/Users/work/Documents/PddGenerator/worker/services/process_grouping_service.py) responsible for building workflow summaries, fallback summaries, and acceptance checks, and keep [draft_generation_stage_services.py](C:/Users/work/Documents/PddGenerator/worker/services/draft_generation_stage_services.py) responsible for stage-level diagram fallback behavior, but replace their direct AI interpreter calls with calls into the new skills.

**Tech Stack:** Python, dataclasses, existing AI skill runtime/client helpers, markdown prompts, worker logging, direct-file unittest-style tests

---

## File Structure

### New files

- `worker/services/ai_skills/process_summary_generation/SKILL.md`
- `worker/services/ai_skills/process_summary_generation/prompt.md`
- `worker/services/ai_skills/process_summary_generation/schemas.py`
- `worker/services/ai_skills/process_summary_generation/skill.py`
- `worker/services/ai_skills/diagram_generation/SKILL.md`
- `worker/services/ai_skills/diagram_generation/prompt.md`
- `worker/services/ai_skills/diagram_generation/schemas.py`
- `worker/services/ai_skills/diagram_generation/skill.py`
- `worker/tests/test_process_summary_generation_skill.py`
- `worker/tests/test_diagram_generation_skill.py`

### Modified files

- `worker/services/ai_skills/registry.py`
- `worker/services/process_grouping_service.py`
- `worker/services/draft_generation_stage_services.py`

### Reference files

- `worker/services/ai_transcript_interpreter.py`
- `worker/services/ai_skills/workflow_group_match/skill.py`
- `worker/services/ai_skills/workflow_boundary_detection/skill.py`

---

### Task 1: Add Process Summary Generation Schemas And Tests

**Files:**
- Create: `worker/services/ai_skills/process_summary_generation/schemas.py`
- Create: `worker/tests/test_process_summary_generation_skill.py`

- [ ] **Step 1: Write the failing schema tests**

```python
from worker.services.ai_skills.process_summary_generation.schemas import (
    ProcessSummaryGenerationRequest,
    ProcessSummaryGenerationResponse,
)


def test_process_summary_request_keeps_workflow_inputs() -> None:
    request = ProcessSummaryGenerationRequest(
        process_title="Vendor Creation",
        workflow_summary={"top_goals": ["Create Vendor"]},
        steps=[{"action_text": "Create vendor"}],
        notes=[{"text": "Uses SAP"}],
        document_type="pdd",
    )

    assert request.process_title == "Vendor Creation"
    assert request.document_type == "pdd"


def test_process_summary_response_keeps_summary_fields() -> None:
    response = ProcessSummaryGenerationResponse(
        summary_text="This workflow creates a vendor in SAP.",
        confidence="high",
        rationale="Clear workflow evidence",
    )

    assert response.summary_text.startswith("This workflow")
    assert response.confidence == "high"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python worker\tests\test_process_summary_generation_skill.py`

Expected: FAIL with missing schema module.

- [ ] **Step 3: Write minimal schema models**

```python
@dataclass(slots=True)
class ProcessSummaryGenerationRequest:
    process_title: str
    workflow_summary: dict[str, object]
    steps: list[dict[str, object]]
    notes: list[dict[str, object]]
    document_type: str


@dataclass(slots=True)
class ProcessSummaryGenerationResponse:
    summary_text: str
    confidence: str = "unknown"
    rationale: str = ""
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python worker\tests\test_process_summary_generation_skill.py`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add worker/services/ai_skills/process_summary_generation/schemas.py worker/tests/test_process_summary_generation_skill.py
git commit -m "Add process summary generation skill schemas"
```

---

### Task 2: Add Process Summary Generation Markdown Assets

**Files:**
- Create: `worker/services/ai_skills/process_summary_generation/SKILL.md`
- Create: `worker/services/ai_skills/process_summary_generation/prompt.md`

- [ ] **Step 1: Add `SKILL.md`**

Include:
- purpose
- inputs and outputs
- sentence-count constraints
- business-language rules
- confidence expectations

- [ ] **Step 2: Add `prompt.md`**

Include:
- strict JSON keys: `summary_text`, `confidence`, `rationale`
- instruction for 2 to 4 plain-English sentences
- instruction to stay scoped to one workflow
- instruction to avoid bullet points and click-by-click UI phrasing

- [ ] **Step 3: Verify files exist**

Run: `Get-ChildItem worker\services\ai_skills\process_summary_generation`

Expected: shows `SKILL.md`, `prompt.md`, `schemas.py`.

- [ ] **Step 4: Commit**

```bash
git add worker/services/ai_skills/process_summary_generation/SKILL.md worker/services/ai_skills/process_summary_generation/prompt.md
git commit -m "Add process summary generation skill markdown assets"
```

---

### Task 3: Implement Process Summary Generation Skill

**Files:**
- Create: `worker/services/ai_skills/process_summary_generation/skill.py`
- Modify: `worker/tests/test_process_summary_generation_skill.py`

- [ ] **Step 1: Write failing tests for normalization and message-building**

Add tests for:
- confidence normalization
- summary text trimming
- `build_messages(...)` containing process title and document type

```python
def test_normalize_confidence_limits_values() -> None:
    assert normalize_confidence("HIGH") == "high"
    assert normalize_confidence("bad") == "medium"


def test_build_messages_includes_summary_context() -> None:
    skill = ProcessSummaryGenerationSkill(client=object())
    request = ProcessSummaryGenerationRequest(
        process_title="Vendor Creation",
        workflow_summary={"top_goals": ["Create Vendor"]},
        steps=[{"action_text": "Create vendor"}],
        notes=[],
        document_type="pdd",
    )

    messages = skill.build_messages(request)

    assert messages[0]["role"] == "system"
    assert "business summary" in messages[0]["content"]
    assert "Vendor Creation" in messages[1]["content"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python worker\tests\test_process_summary_generation_skill.py`

Expected: FAIL with missing `skill.py`.

- [ ] **Step 3: Implement `skill.py`**

The skill should:
- follow the same import fallback pattern as the existing skills
- use the shared AI client/runtime helpers
- normalize blank summaries to `None`
- normalize confidence
- return `ProcessSummaryGenerationResponse | None`

- [ ] **Step 4: Run tests to verify they pass**

Run: `python worker\tests\test_process_summary_generation_skill.py`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add worker/services/ai_skills/process_summary_generation/skill.py worker/tests/test_process_summary_generation_skill.py
git commit -m "Implement process summary generation AI skill"
```

---

### Task 4: Wire Process Summary Generation Into Grouping Service

**Files:**
- Modify: `worker/services/process_grouping_service.py`
- Modify: `worker/tests/test_process_summary_generation_skill.py`

- [ ] **Step 1: Write the failing compatibility test**

Test that the summary path:
- still computes the fallback summary
- uses a stub skill when AI is strong
- keeps the fallback when AI is weak

```python
def test_grouping_service_uses_process_summary_skill_when_confident() -> None:
    service = ProcessGroupingService()
    service._process_summary_generation_skill = StubSummarySkill(
        summary_text="This workflow creates a vendor in SAP.",
        confidence="high",
    )

    process_group = StubProcessGroup(title="Vendor Creation")
    service._refresh_group_summaries(
        process_groups=[process_group],
        transcript_group_ids={"artifact-1": "group-1"},
        steps_by_transcript={"artifact-1": [{"action_text": "Create vendor"}]},
        notes_by_transcript={"artifact-1": []},
        workflow_profiles={"artifact-1": StubWorkflowProfile()},
        document_type="pdd",
    )

    assert process_group.summary_text == "This workflow creates a vendor in SAP."
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python worker\tests\test_process_summary_generation_skill.py`

Expected: FAIL because grouping service still calls the interpreter directly.

- [ ] **Step 3: Update `ProcessGroupingService`**

Implementation notes:
- initialize `self._process_summary_generation_skill` lazily from `build_default_ai_skill_registry()`
- add an INFO log before execution with `skill_id=process_summary_generation`
- preserve the current accepted-confidence check
- preserve fallback summary behavior when the skill returns no usable result

- [ ] **Step 4: Run tests to verify they pass**

Run: `python worker\tests\test_process_summary_generation_skill.py`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add worker/services/process_grouping_service.py worker/tests/test_process_summary_generation_skill.py
git commit -m "Wire process summary generation skill into grouping service"
```

---

### Task 5: Add Diagram Generation Schemas And Tests

**Files:**
- Create: `worker/services/ai_skills/diagram_generation/schemas.py`
- Create: `worker/tests/test_diagram_generation_skill.py`

- [ ] **Step 1: Write the failing schema tests**

```python
from worker.services.ai_skills.diagram_generation.schemas import (
    DiagramGenerationRequest,
    DiagramGenerationResponse,
)


def test_diagram_request_keeps_session_inputs() -> None:
    request = DiagramGenerationRequest(
        session_title="Vendor Workflow",
        diagram_type="flowchart",
        steps=[{"step_number": 1, "action_text": "Create vendor"}],
        notes=[{"text": "Uses SAP"}],
    )

    assert request.session_title == "Vendor Workflow"
    assert request.diagram_type == "flowchart"


def test_diagram_response_keeps_overview_and_detailed_views() -> None:
    response = DiagramGenerationResponse(
        overview={"title": "Overview", "nodes": [], "edges": []},
        detailed={"title": "Detailed", "nodes": [], "edges": []},
    )

    assert response.overview["title"] == "Overview"
    assert response.detailed["title"] == "Detailed"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python worker\tests\test_diagram_generation_skill.py`

Expected: FAIL with missing schema module.

- [ ] **Step 3: Write minimal schema models**

```python
@dataclass(slots=True)
class DiagramGenerationRequest:
    session_title: str
    diagram_type: str
    steps: list[dict[str, object]]
    notes: list[dict[str, object]]


@dataclass(slots=True)
class DiagramGenerationResponse:
    overview: dict[str, object]
    detailed: dict[str, object]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python worker\tests\test_diagram_generation_skill.py`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add worker/services/ai_skills/diagram_generation/schemas.py worker/tests/test_diagram_generation_skill.py
git commit -m "Add diagram generation skill schemas"
```

---

### Task 6: Add Diagram Generation Markdown Assets

**Files:**
- Create: `worker/services/ai_skills/diagram_generation/SKILL.md`
- Create: `worker/services/ai_skills/diagram_generation/prompt.md`

- [ ] **Step 1: Add `SKILL.md`**

Include:
- purpose
- inputs and outputs
- connected-graph constraints
- process-versus-decision node rules
- overview versus detailed graph expectations

- [ ] **Step 2: Add `prompt.md`**

Include:
- strict JSON keys: `overview`, `detailed`
- node and edge shape requirements
- connected graph rules
- decision-node restrictions
- overview compaction guidance and detailed-order preservation guidance

- [ ] **Step 3: Verify files exist**

Run: `Get-ChildItem worker\services\ai_skills\diagram_generation`

Expected: shows `SKILL.md`, `prompt.md`, `schemas.py`.

- [ ] **Step 4: Commit**

```bash
git add worker/services/ai_skills/diagram_generation/SKILL.md worker/services/ai_skills/diagram_generation/prompt.md
git commit -m "Add diagram generation skill markdown assets"
```

---

### Task 7: Implement Diagram Generation Skill

**Files:**
- Create: `worker/services/ai_skills/diagram_generation/skill.py`
- Modify: `worker/tests/test_diagram_generation_skill.py`

- [ ] **Step 1: Write failing tests for normalization and prompt-building**

Add tests for:
- building messages with session title and steps
- normalizing empty node lists into valid empty graph shapes
- preserving overview and detailed keys

```python
def test_build_messages_includes_diagram_context() -> None:
    skill = DiagramGenerationSkill(client=object())
    request = DiagramGenerationRequest(
        session_title="Vendor Workflow",
        diagram_type="flowchart",
        steps=[{"step_number": 1, "action_text": "Create vendor"}],
        notes=[],
    )

    messages = skill.build_messages(request)

    assert messages[0]["role"] == "system"
    assert "flowchart graph models" in messages[0]["content"]
    assert "Vendor Workflow" in messages[1]["content"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python worker\tests\test_diagram_generation_skill.py`

Expected: FAIL with missing `skill.py`.

- [ ] **Step 3: Implement `skill.py`**

The skill should:
- follow the same import fallback pattern as the existing skills
- use the shared AI client/runtime helpers
- return `None` when `diagram_type` is not `flowchart`
- normalize `overview` and `detailed` views into the current graph shape
- preserve node, edge, and title keys
- return `DiagramGenerationResponse | None`

- [ ] **Step 4: Run tests to verify they pass**

Run: `python worker\tests\test_diagram_generation_skill.py`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add worker/services/ai_skills/diagram_generation/skill.py worker/tests/test_diagram_generation_skill.py
git commit -m "Implement diagram generation AI skill"
```

---

### Task 8: Wire Diagram Generation Into Diagram Assembly Stage

**Files:**
- Modify: `worker/services/draft_generation_stage_services.py`
- Modify: `worker/tests/test_diagram_generation_skill.py`

- [ ] **Step 1: Write the failing compatibility test**

Test that `DiagramAssemblyStage.run(...)`:
- uses a stub diagram skill
- writes overview and detailed JSON when output exists
- keeps empty-string fallback when the skill returns no output

```python
def test_diagram_stage_uses_skill_and_serializes_output() -> None:
    stage = DiagramAssemblyStage()
    stage._diagram_generation_skill = StubDiagramSkill(
        overview={"title": "Overview", "nodes": [], "edges": []},
        detailed={"title": "Detailed", "nodes": [], "edges": []},
    )
    context = build_context()

    stage.run(FakeDb(), context)

    assert context.overview_diagram_json == '{"title": "Overview", "nodes": [], "edges": []}'
    assert context.detailed_diagram_json == '{"title": "Detailed", "nodes": [], "edges": []}'
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python worker\tests\test_diagram_generation_skill.py`

Expected: FAIL because the stage still calls the interpreter directly.

- [ ] **Step 3: Update `DiagramAssemblyStage`**

Implementation notes:
- initialize `self._diagram_generation_skill` lazily from `build_default_ai_skill_registry()`
- add an INFO log before execution with `skill_id=diagram_generation`
- preserve the current `try/except` behavior
- preserve empty-string fallback when no diagram output exists

- [ ] **Step 4: Run tests to verify they pass**

Run: `python worker\tests\test_diagram_generation_skill.py`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add worker/services/draft_generation_stage_services.py worker/tests/test_diagram_generation_skill.py
git commit -m "Wire diagram generation skill into draft stage"
```

---

### Task 9: Register The New Skills

**Files:**
- Modify: `worker/services/ai_skills/registry.py`
- Modify: `worker/tests/test_process_summary_generation_skill.py`
- Modify: `worker/tests/test_diagram_generation_skill.py`

- [ ] **Step 1: Write failing registry tests**

Add tests proving `build_default_ai_skill_registry()` can create:
- `process_summary_generation`
- `diagram_generation`

```python
def test_default_registry_creates_generation_skills() -> None:
    registry = build_default_ai_skill_registry()

    assert registry.create("process_summary_generation").skill_id == "process_summary_generation"
    assert registry.create("diagram_generation").skill_id == "diagram_generation"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python worker\tests\test_process_summary_generation_skill.py`

Expected: FAIL with unknown registry keys.

- [ ] **Step 3: Update the registry**

Implementation notes:
- add `_load_process_summary_generation_skill()`
- add `_load_diagram_generation_skill()`
- register both in `build_default_ai_skill_registry()`

- [ ] **Step 4: Run tests to verify they pass**

Run: `python worker\tests\test_process_summary_generation_skill.py`
Run: `python worker\tests\test_diagram_generation_skill.py`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add worker/services/ai_skills/registry.py worker/tests/test_process_summary_generation_skill.py worker/tests/test_diagram_generation_skill.py
git commit -m "Register generation AI skills"
```

---

### Task 10: Run Focused Verification And Capture Runtime Proof Expectations

**Files:**
- Modify: `worker/services/process_grouping_service.py` (if additional log fields are needed)
- Modify: `worker/services/draft_generation_stage_services.py` (if additional log fields are needed)

- [ ] **Step 1: Run the focused test suite**

Run: `python worker\tests\test_ai_skill_runtime.py`
Run: `python worker\tests\test_process_summary_generation_skill.py`
Run: `python worker\tests\test_diagram_generation_skill.py`

Expected: PASS across all three files.

- [ ] **Step 2: Verify runtime logging strings are present in code**

Search:

```powershell
rg -n "process_summary_generation|diagram_generation|Delegating" worker\services\process_grouping_service.py worker\services\draft_generation_stage_services.py
```

Expected: log lines include both skill identifiers.

- [ ] **Step 3: Commit final verification-only adjustments if needed**

```bash
git add worker/services/process_grouping_service.py worker/services/draft_generation_stage_services.py worker/tests/test_process_summary_generation_skill.py worker/tests/test_diagram_generation_skill.py
git commit -m "Finalize generation AI skill migration"
```

- [ ] **Step 4: Manual runtime verification after worker restart**

Run one new generation and confirm worker logs include:
- `skill_id=process_summary_generation`
- `skill_id=diagram_generation`

Expected: real grouping and diagram stages show both AI skill paths before fallback handling.

---

## Self-Review

### Spec coverage

- new process-summary skill: covered by Tasks 1-4
- new diagram skill: covered by Tasks 5-8
- registry wiring: covered by Task 9
- focused tests: covered by Tasks 1, 3, 5, 7, 9, and 10
- runtime logs: covered by Tasks 4, 8, and 10
- keep grouping service as summary orchestration layer: covered by Task 4
- keep diagram stage as fallback layer: covered by Task 8

### Placeholder scan

- no `TODO`, `TBD`, or “implement later” placeholders remain
- every code-changing task names exact files
- every validation task includes explicit commands and expected outcomes

### Type consistency

- request/response types use `ProcessSummaryGenerationRequest/Response` and `DiagramGenerationRequest/Response`
- grouping service still owns fallback/acceptance behavior
- diagram stage still owns empty-output behavior
- registry keys match the planned skill folder names
