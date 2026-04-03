# AI Architecture Contract-First Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor worker-side and backend-side AI integration into a contract-first architecture that follows SOLID principles, shrinks legacy coupling, and keeps orchestration separate from AI execution details.

**Architecture:** Keep orchestration in stage/services, move all AI-facing behavior behind narrow contracts, and resolve concrete implementations through registries/factories at composition roots. Reduce `ai_transcript_interpreter.py` into a temporary adapter while hardening strategy substitution, then remove dead legacy paths once worker and backend follow the same runtime model.

**Tech Stack:** Python, FastAPI, Celery, SQLAlchemy, dataclasses, Protocol, TypedDict, Markdown-based prompts, OpenAI-compatible HTTP client, pytest-style targeted verification

---

## File Structure

### New files

- `worker/services/contracts/__init__.py`
- `worker/services/contracts/transcript_interpretation.py`
- `worker/services/contracts/workflow_intelligence.py`
- `worker/services/contracts/process_grouping.py`
- `worker/services/contracts/diagram_generation.py`
- `backend/app/services/contracts/__init__.py`
- `backend/app/services/contracts/session_grounded_qa.py`
- `backend/app/services/ai_skills/base.py`
- `backend/app/services/ai_skills/runtime.py`
- `worker/tests/test_ai_contracts.py`
- `worker/tests/test_ai_skill_registry_contract_resolution.py`
- `backend/tests/test_session_grounded_qa_contract.py`
- `backend/tests/test_backend_ai_skill_runtime.py`

### Existing files to modify

- `worker/services/ai_skills/base.py`
- `worker/services/ai_skills/runtime.py`
- `worker/services/ai_skills/registry.py`
- `worker/services/ai_transcript_interpreter.py`
- `worker/services/draft_generation_stage_services.py`
- `worker/services/evidence_segmentation_service.py`
- `worker/services/process_grouping_service.py`
- `worker/services/workflow_strategy_interfaces.py`
- `worker/services/workflow_strategy_registry.py`
- `worker/services/draft_generation_worker.py`
- `worker/services/screenshot_generation_worker.py`
- `backend/app/services/session_chat_service.py`
- `backend/app/services/ai_skills/session_grounded_qa/skill.py`

### Responsibility boundaries

- `contracts/`: request/response DTOs + Protocol contracts only
- `ai_skills/`: AI implementation details only
- `draft_generation_*` and `*_service.py`: orchestration, policy, persistence
- `ai_transcript_interpreter.py`: temporary adapter until final removal

---

### Task 1: Create contract baseline

**Files:**
- Create: `worker/services/contracts/__init__.py`
- Create: `worker/services/contracts/transcript_interpretation.py`
- Create: `worker/services/contracts/workflow_intelligence.py`
- Create: `worker/services/contracts/process_grouping.py`
- Create: `worker/services/contracts/diagram_generation.py`
- Create: `backend/app/services/contracts/__init__.py`
- Create: `backend/app/services/contracts/session_grounded_qa.py`
- Test: `worker/tests/test_ai_contracts.py`
- Test: `backend/tests/test_session_grounded_qa_contract.py`

- [ ] **Step 1: Write the failing worker contract test**

```python
from worker.services.contracts.transcript_interpretation import (
    TranscriptInterpretationRequest,
    TranscriptInterpretationResponse,
    TranscriptInterpretationContract,
)
from worker.services.contracts.workflow_intelligence import (
    SemanticEnrichmentContract,
    SemanticEnrichmentRequest,
    WorkflowBoundaryDetectionContract,
)
from worker.services.contracts.process_grouping import (
    ProcessSummaryGenerationContract,
    WorkflowCapabilityTaggingContract,
    WorkflowGroupMatchContract,
    WorkflowTitleResolutionContract,
)
from worker.services.contracts.diagram_generation import DiagramGenerationContract


def test_worker_contract_modules_export_expected_contracts() -> None:
    assert TranscriptInterpretationRequest.__name__ == "TranscriptInterpretationRequest"
    assert TranscriptInterpretationResponse.__name__ == "TranscriptInterpretationResponse"
    assert TranscriptInterpretationContract.__name__ == "TranscriptInterpretationContract"
    assert SemanticEnrichmentRequest.__name__ == "SemanticEnrichmentRequest"
    assert SemanticEnrichmentContract.__name__ == "SemanticEnrichmentContract"
    assert WorkflowBoundaryDetectionContract.__name__ == "WorkflowBoundaryDetectionContract"
    assert WorkflowTitleResolutionContract.__name__ == "WorkflowTitleResolutionContract"
    assert WorkflowGroupMatchContract.__name__ == "WorkflowGroupMatchContract"
    assert ProcessSummaryGenerationContract.__name__ == "ProcessSummaryGenerationContract"
    assert WorkflowCapabilityTaggingContract.__name__ == "WorkflowCapabilityTaggingContract"
    assert DiagramGenerationContract.__name__ == "DiagramGenerationContract"
```

- [ ] **Step 2: Write the failing backend contract test**

```python
from backend.app.services.contracts.session_grounded_qa import (
    SessionGroundedQAContract,
    SessionGroundedQARequestModel,
    SessionGroundedQAResponseModel,
)


def test_backend_session_grounded_qa_contract_exports_expected_types() -> None:
    assert SessionGroundedQARequestModel.__name__ == "SessionGroundedQARequestModel"
    assert SessionGroundedQAResponseModel.__name__ == "SessionGroundedQAResponseModel"
    assert SessionGroundedQAContract.__name__ == "SessionGroundedQAContract"
```

- [ ] **Step 3: Run tests to verify they fail**

Run:

```powershell
python worker\tests\test_ai_contracts.py
python backend\tests\test_session_grounded_qa_contract.py
```

Expected: import errors for missing `contracts` modules

- [ ] **Step 4: Implement worker and backend contracts**

```python
# worker/services/contracts/transcript_interpretation.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(slots=True)
class TranscriptInterpretationRequest:
    transcript_artifact_id: str
    transcript_text: str


@dataclass(slots=True)
class TranscriptInterpretationResponse:
    steps: list[dict[str, Any]]
    notes: list[dict[str, Any]]


class TranscriptInterpretationContract(Protocol):
    def interpret(self, request: TranscriptInterpretationRequest) -> TranscriptInterpretationResponse | None: ...
```

```python
# worker/services/contracts/workflow_intelligence.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True)
class SemanticEnrichmentRequest:
    segment_id: str
    transcript_artifact_id: str
    transcript_text: str
    start_timestamp: str | None
    end_timestamp: str | None


class SemanticEnrichmentContract(Protocol):
    def enrich(self, request: SemanticEnrichmentRequest): ...


class WorkflowBoundaryDetectionContract(Protocol):
    def decide(self, left_segment, right_segment): ...
```

```python
# backend/app/services/contracts/session_grounded_qa.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(slots=True)
class SessionGroundedQARequestModel:
    session_title: str
    process_group_id: str | None
    question: str
    evidence: list[dict[str, str]]


@dataclass(slots=True)
class SessionGroundedQAResponseModel:
    answer: str
    confidence: str
    citation_ids: list[str]


class SessionGroundedQAContract(Protocol):
    def answer(self, request: SessionGroundedQARequestModel) -> SessionGroundedQAResponseModel: ...
```

- [ ] **Step 5: Run tests to verify contracts load**

Run:

```powershell
python worker\tests\test_ai_contracts.py
python backend\tests\test_session_grounded_qa_contract.py
```

Expected: PASS

- [ ] **Step 6: Commit**

```powershell
git add worker/services/contracts backend/app/services/contracts worker/tests/test_ai_contracts.py backend/tests/test_session_grounded_qa_contract.py
git commit -m "Add AI contracts for worker and backend"
```

### Task 2: Standardize worker and backend AI runtimes

**Files:**
- Modify: `worker/services/ai_skills/base.py`
- Modify: `worker/services/ai_skills/runtime.py`
- Modify: `worker/services/ai_skills/registry.py`
- Create: `backend/app/services/ai_skills/base.py`
- Create: `backend/app/services/ai_skills/runtime.py`
- Modify: `backend/app/services/ai_skills/session_grounded_qa/skill.py`
- Test: `worker/tests/test_ai_skill_runtime.py`
- Create: `backend/tests/test_backend_ai_skill_runtime.py`

- [ ] **Step 1: Write the failing backend runtime test**

```python
from backend.app.services.ai_skills.runtime import parse_json_object


def test_backend_ai_runtime_parses_fenced_json_objects() -> None:
    payload = """```json
    {"answer": "ok", "confidence": "high", "citation_ids": []}
    ```"""
    parsed = parse_json_object(payload)
    assert parsed["answer"] == "ok"
```

- [ ] **Step 2: Extend the worker runtime contract test**

```python
from worker.services.ai_skills.runtime import parse_json_object


def test_worker_ai_runtime_parses_fenced_json_objects() -> None:
    payload = """```json
    {"overview": {}, "detailed": {}}
    ```"""
    parsed = parse_json_object(payload)
    assert set(parsed) == {"overview", "detailed"}
```

- [ ] **Step 3: Run tests to verify backend runtime is missing**

Run:

```powershell
python worker\tests\test_ai_skill_runtime.py
python backend\tests\test_backend_ai_skill_runtime.py
```

Expected: backend runtime import error; worker test still passes or requires extension

- [ ] **Step 4: Implement a mirrored backend runtime and tighten worker base abstractions**

```python
# backend/app/services/ai_skills/runtime.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_markdown_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def parse_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```").strip()
        if cleaned.startswith("json"):
            cleaned = cleaned.removeprefix("json").strip()
        if cleaned.endswith("```"):
            cleaned = cleaned.removesuffix("```").strip()
    parsed = json.loads(cleaned)
    if not isinstance(parsed, dict):
        raise ValueError("Expected JSON object.")
    return parsed
```

```python
# worker/services/ai_skills/base.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

TRequest = TypeVar("TRequest")
TResponse = TypeVar("TResponse")


@dataclass(slots=True)
class SkillMetadata:
    skill_id: str
    version: str


class BaseAISkill(Generic[TRequest, TResponse]):
    metadata: SkillMetadata

    def run(self, request: TRequest) -> TResponse:
        raise NotImplementedError
```

- [ ] **Step 5: Update backend session QA skill to use the backend runtime helper**

```python
from backend.app.services.ai_skills.runtime import load_markdown_text, parse_json_object


class SessionGroundedQASkill:
    version = "1.0"
```

- [ ] **Step 6: Run runtime tests**

Run:

```powershell
python worker\tests\test_ai_skill_runtime.py
python backend\tests\test_backend_ai_skill_runtime.py
```

Expected: PASS

- [ ] **Step 7: Commit**

```powershell
git add worker/services/ai_skills/base.py worker/services/ai_skills/runtime.py worker/services/ai_skills/registry.py backend/app/services/ai_skills/base.py backend/app/services/ai_skills/runtime.py backend/app/services/ai_skills/session_grounded_qa/skill.py worker/tests/test_ai_skill_runtime.py backend/tests/test_backend_ai_skill_runtime.py
git commit -m "Standardize worker and backend AI runtimes"
```

### Task 3: Invert orchestration dependencies to contracts

**Files:**
- Modify: `worker/services/draft_generation_stage_services.py`
- Modify: `worker/services/evidence_segmentation_service.py`
- Modify: `worker/services/process_grouping_service.py`
- Modify: `backend/app/services/session_chat_service.py`
- Modify: `worker/services/workflow_strategy_registry.py`
- Create: `worker/tests/test_ai_skill_registry_contract_resolution.py`
- Modify: `worker/tests/test_workflow_boundary_detection_skill.py`
- Modify: `backend/tests/test_session_grounded_qa_skill.py`

- [ ] **Step 1: Write a failing worker orchestration injection test**

```python
from worker.services.workflow_strategy_registry import WorkflowIntelligenceStrategyRegistry


def test_strategy_registry_can_register_contract_backed_factories() -> None:
    registry = WorkflowIntelligenceStrategyRegistry()
    registry.register_enricher("fake", lambda: object())
    strategy = registry.create_strategy_set(
        segmenter_key="paragraph_v1",
        enricher_key="fake",
        boundary_detector_key="heuristic_v1",
    )
    assert strategy.enricher is not None
```

- [ ] **Step 2: Write a failing backend chat-service injection test**

```python
from dataclasses import dataclass

from backend.app.services.contracts.session_grounded_qa import SessionGroundedQAResponseModel
from backend.app.services.session_chat_service import SessionChatService


@dataclass
class FakeSessionGroundedQAContract:
    def answer(self, request):  # type: ignore[no-untyped-def]
        return SessionGroundedQAResponseModel(answer="stub", confidence="high", citation_ids=[])


def test_session_chat_service_accepts_injected_grounded_qa_contract(fake_session) -> None:
    service = SessionChatService(grounded_qa_contract=FakeSessionGroundedQAContract())
    result = service.ask(session=fake_session, question="What happened?")
    assert result["answer"] == "stub"
```

- [ ] **Step 3: Run tests to verify constructor signatures fail**

Run:

```powershell
python worker\tests\test_ai_skill_registry_contract_resolution.py
python backend\tests\test_session_grounded_qa_skill.py
```

Expected: failures from missing injection points or incompatible constructors

- [ ] **Step 4: Refactor orchestrators to depend on contracts**

```python
# backend/app/services/session_chat_service.py
from backend.app.services.contracts.session_grounded_qa import (
    SessionGroundedQAContract,
    SessionGroundedQARequestModel,
)


class SessionChatService:
    def __init__(
        self,
        storage_service: StorageService | None = None,
        grounded_qa_contract: SessionGroundedQAContract | None = None,
    ) -> None:
        self.storage_service = storage_service or StorageService()
        self._grounded_qa_contract = grounded_qa_contract
```

```python
# worker/services/draft_generation_stage_services.py
from worker.services.contracts.transcript_interpretation import TranscriptInterpretationContract


class TranscriptInterpretationStage:
    def __init__(
        self,
        *,
        transcript_interpreter: TranscriptInterpretationContract | None = None,
        ...
    ) -> None:
        self.transcript_interpreter = transcript_interpreter or AITranscriptInterpreter()
```

```python
# worker/services/process_grouping_service.py
from worker.services.contracts.process_grouping import (
    ProcessSummaryGenerationContract,
    WorkflowCapabilityTaggingContract,
    WorkflowGroupMatchContract,
    WorkflowTitleResolutionContract,
)
```

- [ ] **Step 5: Run focused orchestration tests**

Run:

```powershell
python worker\tests\test_ai_skill_registry_contract_resolution.py
python worker\tests\test_workflow_boundary_detection_skill.py
python backend\tests\test_session_grounded_qa_skill.py
```

Expected: PASS

- [ ] **Step 6: Commit**

```powershell
git add worker/services/draft_generation_stage_services.py worker/services/evidence_segmentation_service.py worker/services/process_grouping_service.py worker/services/workflow_strategy_registry.py backend/app/services/session_chat_service.py worker/tests/test_ai_skill_registry_contract_resolution.py worker/tests/test_workflow_boundary_detection_skill.py backend/tests/test_session_grounded_qa_skill.py
git commit -m "Decouple orchestration from concrete AI implementations"
```

### Task 4: Reduce `ai_transcript_interpreter.py` to a legacy adapter

**Files:**
- Modify: `worker/services/ai_transcript_interpreter.py`
- Modify: `worker/services/draft_generation_stage_services.py`
- Modify: `worker/services/process_grouping_service.py`
- Test: `worker/tests/test_ai_transcript_interpreter.py`

- [ ] **Step 1: Write a failing legacy-adapter test**

```python
from worker.services.ai_transcript_interpreter import AITranscriptInterpreter


def test_ai_transcript_interpreter_only_exposes_live_compatibility_methods() -> None:
    interpreter = AITranscriptInterpreter()
    assert hasattr(interpreter, "interpret")
    assert hasattr(interpreter, "resolve_ambiguous_process_group")
```

- [ ] **Step 2: Add a source-structure assertion**

```python
from pathlib import Path


def test_ai_transcript_interpreter_marks_legacy_adapter_section() -> None:
    source = Path("worker/services/ai_transcript_interpreter.py").read_text(encoding="utf-8")
    assert "Legacy compatibility adapter" in source
```

- [ ] **Step 3: Run tests to verify adapter marker is absent**

Run:

```powershell
python worker\tests\test_ai_transcript_interpreter.py
```

Expected: FAIL on missing marker / structure expectation

- [ ] **Step 4: Split legacy-only behavior and remove superseded methods**

```python
class AITranscriptInterpreter:
    """Legacy compatibility adapter for transcript interpretation and ambiguity resolution."""

    def interpret(self, request: TranscriptInterpretationRequest) -> TranscriptInterpretationResponse | None:
        ...

    def resolve_ambiguous_process_group(...):
        ...
```

```python
# remove or deprecate methods no longer used directly
# - interpret_diagrams
# - resolve_workflow_title
# - classify_workflow_boundary
# - enrich_workflow_segment
# - summarize_process_group
# - classify_workflow_capabilities
```

- [ ] **Step 5: Run interpreter and stage tests**

Run:

```powershell
python worker\tests\test_ai_transcript_interpreter.py
python worker\tests\test_ai_skill_runtime.py
```

Expected: PASS

- [ ] **Step 6: Commit**

```powershell
git add worker/services/ai_transcript_interpreter.py worker/services/draft_generation_stage_services.py worker/services/process_grouping_service.py worker/tests/test_ai_transcript_interpreter.py
git commit -m "Reduce AI transcript interpreter to legacy adapter"
```

### Task 5: Harden strategy substitution and fallback policy

**Files:**
- Modify: `worker/services/evidence_segmentation_service.py`
- Modify: `worker/services/process_grouping_service.py`
- Modify: `worker/services/workflow_strategy_interfaces.py`
- Modify: `worker/services/workflow_strategy_registry.py`
- Test: `worker/tests/test_evidence_segmentation_service.py`
- Test: `worker/tests/test_process_grouping_service.py`

- [ ] **Step 1: Write a failing strategy substitution test**

```python
def test_evidence_segmentation_service_accepts_ai_and_heuristic_strategies() -> None:
    service = EvidenceSegmentationService(
        segmenter=ParagraphTranscriptSegmentationStrategy(),
        enricher=HeuristicSemanticEnrichmentStrategy(),
        boundary_detector=HeuristicWorkflowBoundaryStrategy(),
    )
    assert service is not None
```

- [ ] **Step 2: Write a failing grouping fallback-policy test**

```python
def test_process_grouping_service_keeps_policy_outside_ai_contracts(fake_grouping_service) -> None:
    result = fake_grouping_service._normalize_confidence("HIGH")
    assert result == "high"
```

- [ ] **Step 3: Run tests to confirm missing injection seams or policy coupling**

Run:

```powershell
python worker\tests\test_evidence_segmentation_service.py
python worker\tests\test_process_grouping_service.py
```

Expected: at least one failure around constructor rigidity or internal policy assumptions

- [ ] **Step 4: Refactor services so AI and heuristic implementations are true peers**

```python
class EvidenceSegmentationService:
    def __init__(
        self,
        *,
        segmenter: TranscriptSegmentationStrategy,
        enricher: SegmentEnrichmentStrategy,
        boundary_detector: WorkflowBoundaryStrategy,
    ) -> None:
        self.segmenter = segmenter
        self.enricher = enricher
        self.boundary_detector = boundary_detector
```

```python
class ProcessGroupingService:
    _ACCEPTED_AI_CONFIDENCE = {"high", "medium"}

    @staticmethod
    def _normalize_confidence(value: str | None) -> str:
        normalized = str(value or "low").lower()
        return normalized if normalized in {"high", "medium", "low"} else "low"
```

- [ ] **Step 5: Run strategy and grouping tests**

Run:

```powershell
python worker\tests\test_evidence_segmentation_service.py
python worker\tests\test_process_grouping_service.py
python worker\tests\test_workflow_strategy_interfaces.py
```

Expected: PASS

- [ ] **Step 6: Commit**

```powershell
git add worker/services/evidence_segmentation_service.py worker/services/process_grouping_service.py worker/services/workflow_strategy_interfaces.py worker/services/workflow_strategy_registry.py worker/tests/test_evidence_segmentation_service.py worker/tests/test_process_grouping_service.py
git commit -m "Harden workflow strategy substitution and fallback policy"
```

### Task 6: Split pipeline composition into focused coordinators

**Files:**
- Modify: `worker/services/draft_generation_stage_services.py`
- Modify: `worker/services/draft_generation_worker.py`
- Modify: `worker/services/screenshot_generation_worker.py`
- Modify: `worker/services/draft_generation_stage_context.py`
- Test: `worker/tests/test_draft_generation_stage_services.py`
- Test: `worker/tests/test_screenshot_generation_worker.py`

- [ ] **Step 1: Write a failing stage-composition test**

```python
def test_draft_generation_worker_builds_stage_pipeline_explicitly() -> None:
    worker = DraftGenerationWorker()
    stages = worker._build_stages()
    assert [stage.__class__.__name__ for stage in stages]
```

- [ ] **Step 2: Write a failing screenshot-composition test**

```python
def test_screenshot_generation_worker_uses_dedicated_screenshot_coordinator() -> None:
    worker = ScreenshotGenerationWorker()
    assert hasattr(worker, "screenshot_stage")
```

- [ ] **Step 3: Run tests to verify current composition roots are implicit**

Run:

```powershell
python worker\tests\test_draft_generation_stage_services.py
python worker\tests\test_screenshot_generation_worker.py
```

Expected: FAIL on missing `_build_stages()` or screenshot coordinator attribute

- [ ] **Step 4: Introduce smaller composition helpers without changing behavior**

```python
class DraftGenerationWorker:
    def _build_stages(self) -> list[object]:
        return [
            SessionPreparationStage(),
            TranscriptInterpretationStage(),
            EvidenceSegmentationStage(),
            ProcessGroupingStage(),
            CanonicalMergeStage(),
            DiagramAssemblyStage(),
            PersistenceStage(),
        ]
```

```python
class ScreenshotGenerationWorker:
    def __init__(self, screenshot_stage: ScreenshotSelectionStage | None = None) -> None:
        self.screenshot_stage = screenshot_stage or ScreenshotSelectionStage()
```

- [ ] **Step 5: Run pipeline tests**

Run:

```powershell
python worker\tests\test_draft_generation_stage_services.py
python worker\tests\test_screenshot_generation_worker.py
python -m compileall worker
```

Expected: PASS

- [ ] **Step 6: Commit**

```powershell
git add worker/services/draft_generation_stage_services.py worker/services/draft_generation_worker.py worker/services/screenshot_generation_worker.py worker/services/draft_generation_stage_context.py worker/tests/test_draft_generation_stage_services.py worker/tests/test_screenshot_generation_worker.py
git commit -m "Clarify draft and screenshot pipeline composition"
```

### Task 7: Unify worker and backend AI integration conventions

**Files:**
- Modify: `worker/services/ai_skills/registry.py`
- Modify: `worker/services/ai_skills/base.py`
- Modify: `backend/app/services/ai_skills/base.py`
- Modify: `backend/app/services/session_chat_service.py`
- Modify: `backend/app/services/ai_skills/session_grounded_qa/skill.py`
- Test: `worker/tests/test_ai_skill_runtime.py`
- Test: `backend/tests/test_backend_ai_skill_runtime.py`
- Test: `backend/tests/test_session_grounded_qa_skill.py`

- [ ] **Step 1: Write a failing shared-convention test**

```python
def test_backend_and_worker_skills_expose_version_attribute() -> None:
    from worker.services.ai_skills.transcript_to_steps.skill import TranscriptToStepsSkill
    from backend.app.services.ai_skills.session_grounded_qa.skill import SessionGroundedQASkill

    assert TranscriptToStepsSkill.version == "1.0"
    assert SessionGroundedQASkill.version == "1.0"
```

- [ ] **Step 2: Write a failing shared-logging expectation test**

```python
def test_session_grounded_qa_service_logs_skill_metadata(caplog, fake_session) -> None:
    service = SessionChatService(...)
    with caplog.at_level("INFO"):
        ...
    assert "skill_id" in caplog.text
```

- [ ] **Step 3: Run tests to expose mismatched conventions**

Run:

```powershell
python worker\tests\test_ai_skill_runtime.py
python backend\tests\test_backend_ai_skill_runtime.py
python backend\tests\test_session_grounded_qa_skill.py
```

Expected: at least one failure around runtime metadata consistency or shared helper usage

- [ ] **Step 4: Align backend and worker runtime shapes**

```python
# backend/app/services/ai_skills/base.py
from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class BackendSkillMetadata:
    skill_id: str
    version: str
```

```python
# backend/app/services/session_chat_service.py
logger.info(
    "Delegating grounded session Q&A to AI skill.",
    extra={
        "skill_id": self._grounded_qa_contract.skill_id,
        "skill_version": self._grounded_qa_contract.version,
    },
)
```

- [ ] **Step 5: Run cross-boundary AI tests**

Run:

```powershell
python worker\tests\test_ai_skill_runtime.py
python backend\tests\test_backend_ai_skill_runtime.py
python backend\tests\test_session_grounded_qa_skill.py
```

Expected: PASS

- [ ] **Step 6: Commit**

```powershell
git add worker/services/ai_skills/registry.py worker/services/ai_skills/base.py backend/app/services/ai_skills/base.py backend/app/services/session_chat_service.py backend/app/services/ai_skills/session_grounded_qa/skill.py worker/tests/test_ai_skill_runtime.py backend/tests/test_backend_ai_skill_runtime.py backend/tests/test_session_grounded_qa_skill.py
git commit -m "Unify worker and backend AI skill conventions"
```

### Task 8: Remove final dead legacy paths and document the final architecture

**Files:**
- Modify: `worker/services/ai_transcript_interpreter.py`
- Modify: `worker/services/draft_generation_stage_services.py`
- Modify: `worker/services/process_grouping_service.py`
- Modify: `docs/superpowers/specs/2026-04-02-ai-architecture-contract-first-refactor-design.md`
- Test: `worker/tests/test_ai_transcript_interpreter.py`
- Test: `worker/tests/test_ai_skill_runtime.py`
- Test: `backend/tests/test_session_grounded_qa_skill.py`

- [ ] **Step 1: Write a failing dead-path regression test**

```python
from pathlib import Path


def test_removed_legacy_ai_methods_no_longer_exist_in_interpreter() -> None:
    source = Path("worker/services/ai_transcript_interpreter.py").read_text(encoding="utf-8")
    assert "def interpret_diagrams(" not in source
    assert "def classify_workflow_boundary(" not in source
    assert "def summarize_process_group(" not in source
```

- [ ] **Step 2: Run regression test to confirm legacy paths are still present**

Run:

```powershell
python worker\tests\test_ai_transcript_interpreter.py
```

Expected: FAIL on legacy method definitions still present

- [ ] **Step 3: Remove dead code and refresh architecture docs**

```python
# worker/services/ai_transcript_interpreter.py
class AITranscriptInterpreter:
    """Legacy compatibility adapter for the remaining transcript interpretation path."""
```

```markdown
## Final state

- worker orchestration depends on contracts
- AI implementations live under `ai_skills`
- backend session Q&A follows the same contract-first pattern
- `ai_transcript_interpreter.py` is adapter-only or removed
```

- [ ] **Step 4: Run final focused verification**

Run:

```powershell
python worker\tests\test_ai_transcript_interpreter.py
python worker\tests\test_ai_skill_runtime.py
python backend\tests\test_session_grounded_qa_skill.py
python -m compileall worker
python -m compileall app
```

Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add worker/services/ai_transcript_interpreter.py worker/services/draft_generation_stage_services.py worker/services/process_grouping_service.py docs/superpowers/specs/2026-04-02-ai-architecture-contract-first-refactor-design.md worker/tests/test_ai_transcript_interpreter.py worker/tests/test_ai_skill_runtime.py backend/tests/test_session_grounded_qa_skill.py
git commit -m "Finalize contract-first AI architecture"
```

---

## Verification Matrix

- Phase 1 verifies contract modules load and export stable types
- Phase 2 verifies runtime parsing and shared execution helpers
- Phase 3 verifies orchestration accepts injected contract implementations
- Phase 4 verifies `ai_transcript_interpreter.py` is reduced to a clear compatibility adapter
- Phase 5 verifies AI and heuristic strategies are substitutable
- Phase 6 verifies worker composition roots are explicit and smaller
- Phase 7 verifies backend and worker AI integrations follow the same conventions
- Phase 8 verifies legacy dead paths are removed and the final architecture still compiles

## Commit Sequence

1. `Add AI contracts for worker and backend`
2. `Standardize worker and backend AI runtimes`
3. `Decouple orchestration from concrete AI implementations`
4. `Reduce AI transcript interpreter to legacy adapter`
5. `Harden workflow strategy substitution and fallback policy`
6. `Clarify draft and screenshot pipeline composition`
7. `Unify worker and backend AI skill conventions`
8. `Finalize contract-first AI architecture`
