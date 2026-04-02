# Hybrid AI Skills Session Grounded QA Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate grounded session Q&A into a backend hybrid AI skill while keeping `SessionChatService` responsible for evidence gathering, citation filtering, and final API response mapping.

**Architecture:** Add one backend-side skill under `backend/app/services/ai_skills/`: `session_grounded_qa`. Keep [session_chat_service.py](C:/Users/work/Documents/PddGenerator/backend/app/services/session_chat_service.py) as the orchestration and grounding layer, but replace its direct OpenAI-compatible request/response logic with a call into the new skill so only AI behavior moves.

**Tech Stack:** Python, dataclasses, existing backend settings/httpx pattern, markdown prompts, backend logging, direct-file unittest-style tests

---

## File Structure

### New files

- `backend/app/services/ai_skills/session_grounded_qa/README.md`
- `backend/app/services/ai_skills/session_grounded_qa/prompt.md`
- `backend/app/services/ai_skills/session_grounded_qa/schemas.py`
- `backend/app/services/ai_skills/session_grounded_qa/skill.py`
- `backend/tests/test_session_grounded_qa_skill.py`

### Modified files

- `backend/app/services/session_chat_service.py`

### Reference files

- `backend/app/api/routes/draft_sessions.py`
- `backend/app/schemas/draft_session.py`
- `backend/app/services/session_chat_service.py`

---

### Task 1: Add Session Grounded QA Schemas And Tests

**Files:**
- Create: `backend/app/services/ai_skills/session_grounded_qa/schemas.py`
- Create: `backend/tests/test_session_grounded_qa_skill.py`

- [ ] **Step 1: Write the failing schema tests**

```python
from app.services.ai_skills.session_grounded_qa.schemas import (
    SessionGroundedQARequest,
    SessionGroundedQAResponse,
)


def test_session_grounded_qa_request_keeps_inputs() -> None:
    request = SessionGroundedQARequest(
        session_title="Quarterly Procurement Review",
        process_group_id="group-1",
        question="What is the approval step?",
        evidence=[{"id": "step-1", "source_type": "step", "title": "Step 1", "content": "Approve PO"}],
    )

    assert request.session_title == "Quarterly Procurement Review"
    assert request.question == "What is the approval step?"


def test_session_grounded_qa_response_keeps_outputs() -> None:
    response = SessionGroundedQAResponse(
        answer="The approval happens after purchase order review.",
        confidence="high",
        citation_ids=["step-1"],
    )

    assert response.confidence == "high"
    assert response.citation_ids == ["step-1"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python backend\tests\test_session_grounded_qa_skill.py`

Expected: FAIL with missing schema module.

- [ ] **Step 3: Write minimal schema models**

```python
from dataclasses import dataclass


@dataclass(slots=True)
class SessionGroundedQARequest:
    session_title: str
    process_group_id: str | None
    question: str
    evidence: list[dict[str, object]]


@dataclass(slots=True)
class SessionGroundedQAResponse:
    answer: str
    confidence: str = "medium"
    citation_ids: list[str] | None = None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python backend\tests\test_session_grounded_qa_skill.py`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/ai_skills/session_grounded_qa/schemas.py backend/tests/test_session_grounded_qa_skill.py
git commit -m "Add session grounded QA skill schemas"
```

---

### Task 2: Add Session Grounded QA Markdown Assets

**Files:**
- Create: `backend/app/services/ai_skills/session_grounded_qa/README.md`
- Create: `backend/app/services/ai_skills/session_grounded_qa/prompt.md`

- [ ] **Step 1: Add `README.md`**

Include:
- purpose
- inputs and outputs
- grounding-only rule
- citation-id rule
- confidence expectations

- [ ] **Step 2: Add `prompt.md`**

Include:
- strict JSON keys: `answer`, `confidence`, `citation_ids`
- instruction to use only supplied evidence
- instruction to say when evidence is insufficient
- instruction that citation ids must reference used evidence

- [ ] **Step 3: Verify files exist**

Run: `Get-ChildItem backend\app\services\ai_skills\session_grounded_qa`

Expected: shows `README.md`, `prompt.md`, `schemas.py`.

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/ai_skills/session_grounded_qa/README.md backend/app/services/ai_skills/session_grounded_qa/prompt.md
git commit -m "Add session grounded QA skill markdown assets"
```

---

### Task 3: Implement Session Grounded QA Skill

**Files:**
- Create: `backend/app/services/ai_skills/session_grounded_qa/skill.py`
- Modify: `backend/tests/test_session_grounded_qa_skill.py`

- [ ] **Step 1: Write failing tests for normalization and message-building**

Add tests for:
- confidence normalization
- citation-id normalization
- `build_messages(...)` containing the question and evidence

```python
def test_normalize_confidence_limits_values() -> None:
    assert normalize_confidence("HIGH") == "high"
    assert normalize_confidence("bad") == "medium"


def test_normalize_citation_ids_filters_blank_values() -> None:
    assert normalize_citation_ids(["step-1", "", None, "note-1"]) == ["step-1", "note-1"]


def test_build_messages_includes_question_and_evidence() -> None:
    skill = SessionGroundedQASkill(client=object(), settings=FakeSettings())
    request = SessionGroundedQARequest(
        session_title="Quarterly Procurement Review",
        process_group_id="group-1",
        question="What is the approval step?",
        evidence=[{"id": "step-1", "source_type": "step", "title": "Step 1", "content": "Approve PO"}],
    )

    messages = skill.build_messages(request)

    assert messages[0]["role"] == "system"
    assert "Use only the supplied evidence" in messages[0]["content"]
    assert "What is the approval step?" in messages[1]["content"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python backend\tests\test_session_grounded_qa_skill.py`

Expected: FAIL with missing `skill.py`.

- [ ] **Step 3: Implement `skill.py`**

The skill should:
- load prompt content from markdown
- use `get_settings()` and `httpx` in the same pattern as the current service
- call the OpenAI-compatible endpoint
- parse JSON response
- normalize confidence to `high|medium|low`
- normalize citation ids to a clean list of strings
- return `SessionGroundedQAResponse`

- [ ] **Step 4: Run tests to verify they pass**

Run: `python backend\tests\test_session_grounded_qa_skill.py`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/ai_skills/session_grounded_qa/skill.py backend/tests/test_session_grounded_qa_skill.py
git commit -m "Implement session grounded QA AI skill"
```

---

### Task 4: Wire Session Grounded QA Into Session Chat Service

**Files:**
- Modify: `backend/app/services/session_chat_service.py`
- Modify: `backend/tests/test_session_grounded_qa_skill.py`

- [ ] **Step 1: Write the failing compatibility tests**

Add tests for:
- `SessionChatService.ask(...)` delegates to the skill
- invalid citation ids are still filtered out by the service
- blank answer still falls back to the current insufficient-evidence message

```python
def test_session_chat_service_uses_grounded_qa_skill() -> None:
    service = SessionChatService(storage_service=FakeStorageService())
    service._session_grounded_qa_skill = StubSessionGroundedQASkill(
        answer="The approval happens after review.",
        confidence="high",
        citation_ids=["step-1"],
    )

    response = service.ask(session=build_session(), question="What is the approval step?")

    assert response["answer"] == "The approval happens after review."
    assert response["confidence"] == "high"
    assert response["citations"][0]["id"] == "step-1"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python backend\tests\test_session_grounded_qa_skill.py`

Expected: FAIL because the service still performs the AI request directly.

- [ ] **Step 3: Update `SessionChatService`**

Implementation notes:
- lazily initialize `self._session_grounded_qa_skill`
- add an INFO log before execution with `skill_id=session_grounded_qa`
- preserve current AI-enabled and blank-question checks
- preserve `_build_evidence_items(...)`
- preserve citation filtering against valid evidence ids
- preserve the fallback answer when the returned answer is blank

- [ ] **Step 4: Run tests to verify they pass**

Run: `python backend\tests\test_session_grounded_qa_skill.py`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/session_chat_service.py backend/tests/test_session_grounded_qa_skill.py
git commit -m "Wire session grounded QA skill into session chat service"
```

---

### Task 5: Run Focused Verification And Capture Runtime Proof Expectations

**Files:**
- Modify: `backend/app/services/session_chat_service.py` (if additional log fields are needed)

- [ ] **Step 1: Run the focused test suite**

Run: `python backend\tests\test_session_grounded_qa_skill.py`

Expected: PASS.

- [ ] **Step 2: Verify runtime logging strings are present in code**

Search:

```powershell
rg -n "session_grounded_qa|Delegating grounded session Q&A" backend\app\services\session_chat_service.py backend\app\services\ai_skills\session_grounded_qa\skill.py
```

Expected: log lines include the `session_grounded_qa` skill identifier.

- [ ] **Step 3: Commit final verification-only adjustments if needed**

```bash
git add backend/app/services/session_chat_service.py backend/tests/test_session_grounded_qa_skill.py
git commit -m "Finalize session grounded QA AI skill migration"
```

- [ ] **Step 4: Manual runtime verification**

Call the existing session question route and confirm the backend logs include:
- `skill_id=session_grounded_qa`

Expected: the session question path shows service delegation and skill execution before citation filtering.

---

## Self-Review

### Spec coverage

- new backend grounded-QA skill: covered by Tasks 1-3
- service integration: covered by Task 4
- preserve evidence building and citation filtering: covered by Task 4
- focused tests: covered by Tasks 1, 3, 4, and 5
- runtime logs: covered by Tasks 4 and 5

### Placeholder scan

- no `TODO`, `TBD`, or “implement later” placeholders remain
- every code-changing task names exact files
- every validation task includes explicit commands and expected outcomes

### Type consistency

- request/response types use `SessionGroundedQARequest/Response`
- session chat service still owns evidence building and citation shaping
- runtime logging uses the `session_grounded_qa` skill identifier
