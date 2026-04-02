# Hybrid AI Skills Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Introduce a hybrid worker-side AI skill framework and migrate transcript-to-steps interpretation into the first real skill without breaking the existing worker pipeline.

**Architecture:** Add a small `worker/services/ai_skills/` framework with a shared client, runtime helpers, registry, and typed skill contract. Implement one concrete `transcript_to_steps` skill with markdown-based skill/prompt files and Python-based execution/schemas, then delegate the current interpreter's transcript path to that skill while preserving current external behavior.

**Tech Stack:** Python, httpx, dataclasses/typing, pytest/unittest-style worker tests, markdown-loaded prompts, Git

---

## File Structure

### New files

- `worker/services/ai_skills/base.py`
  - minimal typed skill protocol and shared metadata
- `worker/services/ai_skills/client.py`
  - shared OpenAI-compatible HTTP client wrapper
- `worker/services/ai_skills/runtime.py`
  - prompt loading, JSON parsing, and normalization helpers
- `worker/services/ai_skills/registry.py`
  - local registry for skill resolution
- `worker/services/ai_skills/transcript_to_steps/SKILL.md`
  - human-readable skill intent and constraints
- `worker/services/ai_skills/transcript_to_steps/prompt.md`
  - prompt text for the model
- `worker/services/ai_skills/transcript_to_steps/schemas.py`
  - request/response dataclasses for the skill
- `worker/services/ai_skills/transcript_to_steps/skill.py`
  - runtime execution of the transcript-to-steps skill
- `worker/tests/test_ai_skill_runtime.py`
  - shared runtime helper tests
- `worker/tests/test_transcript_to_steps_skill.py`
  - skill behavior tests

### Modified files

- `worker/services/ai_transcript_interpreter.py`
  - delegate transcript interpretation to the new skill while preserving its public shape
- `worker/tests/test_draft_generation_worker.py`
  - update or extend compatibility coverage if current tests depend on transcript interpretation behavior

### Existing files to reference while implementing

- `worker/services/workflow_strategy_interfaces.py`
  - style reference for simple explicit protocols
- `worker/services/workflow_strategy_registry.py`
  - registry style reference
- `worker/services/ai_transcript_interpreter.py`
  - source behavior to preserve
- `backend/app/services/step_extraction.py`
  - deterministic fallback shape reference

---

### Task 1: Add Failing Tests For Runtime Helpers

**Files:**
- Create: `worker/tests/test_ai_skill_runtime.py`
- Create later in implementation: `worker/services/ai_skills/runtime.py`

- [ ] **Step 1: Write the failing tests for prompt loading and JSON parsing**

```python
from pathlib import Path

import pytest

from worker.services.ai_skills.runtime import load_markdown_text, parse_json_object


def test_load_markdown_text_reads_existing_file(tmp_path: Path) -> None:
    prompt_file = tmp_path / "prompt.md"
    prompt_file.write_text("system prompt", encoding="utf-8")

    assert load_markdown_text(prompt_file) == "system prompt"


def test_parse_json_object_accepts_plain_json() -> None:
    parsed = parse_json_object('{"answer": "ok"}')

    assert parsed == {"answer": "ok"}


def test_parse_json_object_accepts_fenced_json() -> None:
    parsed = parse_json_object('```json\n{"answer": "ok"}\n```')

    assert parsed == {"answer": "ok"}


def test_parse_json_object_rejects_non_object_json() -> None:
    with pytest.raises(ValueError, match="JSON object"):
        parse_json_object('["not", "object"]')
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest worker/tests/test_ai_skill_runtime.py -v`

Expected: FAIL with import errors because `worker.services.ai_skills.runtime` does not exist yet.

- [ ] **Step 3: Write minimal runtime implementation**

```python
import json
from pathlib import Path
from typing import Any


def load_markdown_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def parse_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:].strip()
    parsed = json.loads(cleaned)
    if not isinstance(parsed, dict):
        raise ValueError("Expected JSON object from AI skill response.")
    return parsed
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest worker/tests/test_ai_skill_runtime.py -v`

Expected: PASS for all 4 tests.

- [ ] **Step 5: Commit**

```bash
git add worker/tests/test_ai_skill_runtime.py worker/services/ai_skills/runtime.py
git commit -m "Add AI skill runtime helpers"
```

---

### Task 2: Add The Base Skill Contract And Registry

**Files:**
- Create: `worker/services/ai_skills/base.py`
- Create: `worker/services/ai_skills/registry.py`
- Reference: `worker/services/workflow_strategy_interfaces.py`
- Reference: `worker/services/workflow_strategy_registry.py`

- [ ] **Step 1: Write the failing test for registry resolution**

Add this test to `worker/tests/test_ai_skill_runtime.py`:

```python
from dataclasses import dataclass

from worker.services.ai_skills.registry import AISkillRegistry


@dataclass
class DummySkill:
    skill_id: str = "dummy"
    version: str = "1.0"

    def run(self, input: object) -> object:
        return input


def test_skill_registry_resolves_registered_skill() -> None:
    registry = AISkillRegistry()
    registry.register("dummy", lambda: DummySkill())

    skill = registry.create("dummy")

    assert skill.skill_id == "dummy"
    assert skill.version == "1.0"


def test_skill_registry_rejects_unknown_skill() -> None:
    registry = AISkillRegistry()

    with pytest.raises(ValueError, match="Unknown AI skill"):
        registry.create("missing")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest worker/tests/test_ai_skill_runtime.py -v`

Expected: FAIL with missing `registry.py`.

- [ ] **Step 3: Write minimal base contract and registry**

`worker/services/ai_skills/base.py`

```python
from __future__ import annotations

from typing import Any, Protocol


class AISkill(Protocol):
    skill_id: str
    version: str

    def run(self, input: Any) -> Any:
        ...
```

`worker/services/ai_skills/registry.py`

```python
from __future__ import annotations

from collections.abc import Callable

from worker.services.ai_skills.base import AISkill


class AISkillRegistry:
    def __init__(self) -> None:
        self._skills: dict[str, Callable[[], AISkill]] = {}

    def register(self, key: str, factory: Callable[[], AISkill]) -> None:
        self._skills[key] = factory

    def create(self, key: str) -> AISkill:
        try:
            return self._skills[key]()
        except KeyError as exc:
            available = ", ".join(sorted(self._skills)) or "none"
            raise ValueError(f"Unknown AI skill '{key}'. Available: {available}.") from exc
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest worker/tests/test_ai_skill_runtime.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add worker/tests/test_ai_skill_runtime.py worker/services/ai_skills/base.py worker/services/ai_skills/registry.py
git commit -m "Add AI skill base contract and registry"
```

---

### Task 3: Add Shared AI Client Transport

**Files:**
- Create: `worker/services/ai_skills/client.py`
- Modify: `worker/tests/test_ai_skill_runtime.py`
- Reference: `worker/services/ai_transcript_interpreter.py`

- [ ] **Step 1: Write the failing tests for content extraction**

Add these tests to `worker/tests/test_ai_skill_runtime.py`:

```python
from worker.services.ai_skills.client import extract_message_content


def test_extract_message_content_accepts_string_content() -> None:
    body = {"choices": [{"message": {"content": '{"steps": [], "notes": []}'}}]}

    assert extract_message_content(body) == '{"steps": [], "notes": []}'
```

Add this second test in the same file:

```python
def test_extract_message_content_accepts_list_content() -> None:
    body = {
        "choices": [
            {
                "message": {
                    "content": [
                        {"text": '{"steps": []'},
                        {"text": ', "notes": []}'},
                    ]
                }
            }
        ]
    }

    assert extract_message_content(body) == '{"steps": [], "notes": []}'
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest worker/tests/test_ai_skill_runtime.py -v`

Expected: FAIL with missing `client.py`.

- [ ] **Step 3: Write minimal shared client helpers**

`worker/services/ai_skills/client.py`

```python
from __future__ import annotations

from typing import Any

import httpx

from worker.bootstrap import get_backend_settings


def extract_message_content(response_body: dict[str, Any]) -> str:
    choices = response_body.get("choices", [])
    if not choices:
        raise ValueError("AI skill response did not contain any choices.")

    message = choices[0].get("message", {})
    content = message.get("content", "")
    if isinstance(content, list):
        return "".join(item.get("text", "") for item in content if isinstance(item, dict))
    if isinstance(content, str):
        return content
    raise ValueError("AI skill response content was not in a supported format.")


class OpenAICompatibleSkillClient:
    def __init__(self) -> None:
        self.settings = get_backend_settings()

    def is_enabled(self) -> bool:
        return bool(
            self.settings.ai_enabled
            and self.settings.ai_api_key
            and self.settings.ai_base_url
            and self.settings.ai_model
        )

    def post_json(self, *, messages: list[dict[str, str]], temperature: float = 0.1) -> dict[str, Any]:
        endpoint = f"{self.settings.ai_base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.settings.ai_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.settings.ai_model,
            "temperature": temperature,
            "response_format": {"type": "json_object"},
            "messages": messages,
        }
        timeout = httpx.Timeout(self.settings.ai_timeout_seconds)
        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.post(endpoint, headers=headers, json=payload)
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException as exc:
            raise RuntimeError(
                f"AI skill request timed out after {self.settings.ai_timeout_seconds:.0f} seconds."
            ) from exc
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code if exc.response is not None else "unknown"
            raise RuntimeError(f"AI skill request failed with HTTP {status_code}.") from exc
        except httpx.HTTPError as exc:
            raise RuntimeError(f"AI skill request failed: {exc.__class__.__name__}.") from exc
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest worker/tests/test_ai_skill_runtime.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add worker/tests/test_ai_skill_runtime.py worker/services/ai_skills/client.py
git commit -m "Add shared AI skill client"
```

---

### Task 4: Add Transcript-To-Steps Schema Tests And Models

**Files:**
- Create: `worker/services/ai_skills/transcript_to_steps/schemas.py`
- Create: `worker/tests/test_transcript_to_steps_skill.py`

- [ ] **Step 1: Write the failing tests for transcript-to-steps schemas**

```python
from worker.services.ai_skills.transcript_to_steps.schemas import (
    TranscriptNote,
    TranscriptStep,
    TranscriptToStepsRequest,
    TranscriptToStepsResponse,
)


def test_transcript_to_steps_response_holds_steps_and_notes() -> None:
    response = TranscriptToStepsResponse(
        steps=[
            TranscriptStep(
                application_name="SAP",
                action_text="Open vendor transaction",
                source_data_note="",
                start_timestamp="00:00:05",
                end_timestamp="00:00:08",
                display_timestamp="00:00:05",
                supporting_transcript_text="Open vendor transaction",
                confidence="high",
            )
        ],
        notes=[TranscriptNote(text="Vendor must exist first", confidence="medium", inference_type="inferred")],
    )

    assert response.steps[0].application_name == "SAP"
    assert response.notes[0].inference_type == "inferred"


def test_transcript_to_steps_request_keeps_transcript_input() -> None:
    request = TranscriptToStepsRequest(
        transcript_artifact_id="artifact-1",
        transcript_text="00:00:01 Open SAP",
    )

    assert request.transcript_artifact_id == "artifact-1"
    assert "Open SAP" in request.transcript_text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest worker/tests/test_transcript_to_steps_skill.py -v`

Expected: FAIL with missing schema module.

- [ ] **Step 3: Write minimal schema models**

`worker/services/ai_skills/transcript_to_steps/schemas.py`

```python
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class TranscriptToStepsRequest:
    transcript_artifact_id: str
    transcript_text: str


@dataclass(slots=True)
class TranscriptStep:
    application_name: str
    action_text: str
    source_data_note: str
    start_timestamp: str
    end_timestamp: str
    display_timestamp: str
    supporting_transcript_text: str
    confidence: str


@dataclass(slots=True)
class TranscriptNote:
    text: str
    confidence: str
    inference_type: str


@dataclass(slots=True)
class TranscriptToStepsResponse:
    steps: list[TranscriptStep] = field(default_factory=list)
    notes: list[TranscriptNote] = field(default_factory=list)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest worker/tests/test_transcript_to_steps_skill.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add worker/tests/test_transcript_to_steps_skill.py worker/services/ai_skills/transcript_to_steps/schemas.py
git commit -m "Add transcript-to-steps skill schemas"
```

---

### Task 5: Add Markdown Skill Assets

**Files:**
- Create: `worker/services/ai_skills/transcript_to_steps/SKILL.md`
- Create: `worker/services/ai_skills/transcript_to_steps/prompt.md`

- [ ] **Step 1: Add the skill definition markdown**

`worker/services/ai_skills/transcript_to_steps/SKILL.md`

```md
# Transcript To Steps

## Purpose

Convert one grounded transcript into structured process steps and business-rule notes.

## Inputs

- `transcript_artifact_id`
- `transcript_text`

## Outputs

- `steps`
- `notes`

## Rules

- use only transcript evidence provided
- do not invent timestamps
- do not invent application names not supported by transcript text
- ignore greetings, filler talk, and non-process chatter
- `supporting_transcript_text` must contain the exact supporting transcript snippet
- confidence must be one of `high`, `medium`, `low`, `unknown`
```

- [ ] **Step 2: Add the prompt markdown**

`worker/services/ai_skills/transcript_to_steps/prompt.md`

```md
You convert RPA discovery transcripts into structured process steps and business rules.

Return strict JSON with two keys: `steps` and `notes`.

Each step must include:
- `application_name`
- `action_text`
- `source_data_note`
- `start_timestamp`
- `end_timestamp`
- `display_timestamp`
- `supporting_transcript_text`
- `confidence`

Each note must include:
- `text`
- `confidence`
- `inference_type`

Rules:
- Ignore greetings, filler talk, and YouTube-style intros.
- Prefer timestamps from the transcript when present.
- Every returned timestamp must be in `HH:MM:SS` format.
- If a step has no clear timestamp, return an empty string for that field.
- `supporting_transcript_text` must contain the exact transcript snippet that supports the step.
- `display_timestamp` should be the best single timestamp to show in UI and export.
- Confidence must be one of `high`, `medium`, `low`, `unknown`.
```

- [ ] **Step 3: Run a quick file existence check**

Run: `Get-ChildItem worker\\services\\ai_skills\\transcript_to_steps`

Expected: shows `SKILL.md`, `prompt.md`, and `schemas.py`.

- [ ] **Step 4: Commit**

```bash
git add worker/services/ai_skills/transcript_to_steps/SKILL.md worker/services/ai_skills/transcript_to_steps/prompt.md
git commit -m "Add transcript-to-steps skill markdown assets"
```

---

### Task 6: Implement The Transcript-To-Steps Skill

**Files:**
- Create: `worker/services/ai_skills/transcript_to_steps/skill.py`
- Modify: `worker/tests/test_transcript_to_steps_skill.py`
- Reference: `worker/services/ai_transcript_interpreter.py`

- [ ] **Step 1: Write the failing tests for skill execution helpers**

Add to `worker/tests/test_transcript_to_steps_skill.py`:

```python
from worker.services.ai_skills.transcript_to_steps.skill import (
    TranscriptToStepsSkill,
    normalize_confidence,
    normalize_timestamp,
)


def test_normalize_confidence_limits_values() -> None:
    assert normalize_confidence("HIGH") == "high"
    assert normalize_confidence("bad-value") == "medium"


def test_normalize_timestamp_converts_hms() -> None:
    assert normalize_timestamp("1:02:03") == "01:02:03"
    assert normalize_timestamp("") == ""


def test_build_messages_includes_prompt_and_transcript() -> None:
    skill = TranscriptToStepsSkill()
    request = TranscriptToStepsRequest(transcript_artifact_id="artifact-1", transcript_text="00:00:01 Open SAP")

    messages = skill.build_messages(request)

    assert messages[0]["role"] == "system"
    assert "structured process steps" in messages[0]["content"]
    assert "Open SAP" in messages[1]["content"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest worker/tests/test_transcript_to_steps_skill.py -v`

Expected: FAIL with missing skill module.

- [ ] **Step 3: Write minimal skill implementation**

`worker/services/ai_skills/transcript_to_steps/skill.py`

```python
from __future__ import annotations

import re
from pathlib import Path

from worker.services.ai_skills.client import OpenAICompatibleSkillClient, extract_message_content
from worker.services.ai_skills.runtime import load_markdown_text, parse_json_object
from worker.services.ai_skills.transcript_to_steps.schemas import (
    TranscriptNote,
    TranscriptStep,
    TranscriptToStepsRequest,
    TranscriptToStepsResponse,
)

TIMESTAMP_PATTERN = re.compile(r"\b(?:(\d{1,2}):)?(\d{1,2}):(\d{2})\b")


def normalize_confidence(value: str) -> str:
    normalized = str(value or "medium").lower()
    return normalized if normalized in {"high", "medium", "low", "unknown"} else "medium"


def normalize_timestamp(value: str) -> str:
    if not value:
        return ""
    match = TIMESTAMP_PATTERN.search(value.strip())
    if not match:
        return ""
    hours_group, minutes_group, seconds_group = match.groups()
    hours = int(hours_group or 0)
    minutes = int(minutes_group)
    seconds = int(seconds_group)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


class TranscriptToStepsSkill:
    skill_id = "transcript_to_steps"
    version = "1.0"

    def __init__(self, client: OpenAICompatibleSkillClient | None = None) -> None:
        self.client = client or OpenAICompatibleSkillClient()

    def build_messages(self, request: TranscriptToStepsRequest) -> list[dict[str, str]]:
        prompt_path = Path(__file__).with_name("prompt.md")
        prompt_text = load_markdown_text(prompt_path)
        return [
            {"role": "system", "content": prompt_text},
            {
                "role": "user",
                "content": f"Convert this transcript into process steps and business rules.\n\nTranscript:\n{request.transcript_text}",
            },
        ]

    def run(self, input: TranscriptToStepsRequest) -> TranscriptToStepsResponse:
        response_body = self.client.post_json(messages=self.build_messages(input))
        content = extract_message_content(response_body)
        parsed = parse_json_object(content)
        steps = [
            TranscriptStep(
                application_name=str(item.get("application_name", "") or ""),
                action_text=str(item.get("action_text", "") or "").strip(),
                source_data_note=str(item.get("source_data_note", "") or "").strip(),
                start_timestamp=normalize_timestamp(str(item.get("start_timestamp", "") or "")),
                end_timestamp=normalize_timestamp(str(item.get("end_timestamp", "") or "")),
                display_timestamp=normalize_timestamp(str(item.get("display_timestamp", item.get("timestamp", "")) or "")),
                supporting_transcript_text=str(item.get("supporting_transcript_text", "") or "").strip(),
                confidence=normalize_confidence(str(item.get("confidence", "") or "")),
            )
            for item in parsed.get("steps", [])
            if isinstance(item, dict)
        ]
        notes = [
            TranscriptNote(
                text=str(item.get("text", "") or "").strip(),
                confidence=normalize_confidence(str(item.get("confidence", "") or "")),
                inference_type=str(item.get("inference_type", "inferred") or "inferred"),
            )
            for item in parsed.get("notes", [])
            if isinstance(item, dict)
        ]
        return TranscriptToStepsResponse(steps=steps, notes=notes)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest worker/tests/test_transcript_to_steps_skill.py -v`

Expected: PASS for normalization and prompt-building tests.

- [ ] **Step 5: Commit**

```bash
git add worker/tests/test_transcript_to_steps_skill.py worker/services/ai_skills/transcript_to_steps/skill.py
git commit -m "Implement transcript-to-steps AI skill"
```

---

### Task 7: Add A Compatibility Test For The Existing Interpreter Shape

**Files:**
- Modify: `worker/tests/test_transcript_to_steps_skill.py`
- Modify later in implementation: `worker/services/ai_transcript_interpreter.py`

- [ ] **Step 1: Write the failing compatibility test**

Add to `worker/tests/test_transcript_to_steps_skill.py`:

```python
from worker.services.ai_transcript_interpreter import AITranscriptInterpreter
from worker.services.ai_skills.transcript_to_steps.schemas import (
    TranscriptNote,
    TranscriptStep,
    TranscriptToStepsResponse,
)


class StubTranscriptSkill:
    skill_id = "transcript_to_steps"
    version = "1.0"

    def run(self, input: object) -> TranscriptToStepsResponse:
        return TranscriptToStepsResponse(
            steps=[
                TranscriptStep(
                    application_name="SAP",
                    action_text="Open vendor transaction",
                    source_data_note="",
                    start_timestamp="00:00:05",
                    end_timestamp="00:00:06",
                    display_timestamp="00:00:05",
                    supporting_transcript_text="Open vendor transaction",
                    confidence="high",
                )
            ],
            notes=[TranscriptNote(text="Vendor must exist", confidence="medium", inference_type="inferred")],
        )


def test_interpret_uses_transcript_skill_and_preserves_legacy_shape() -> None:
    interpreter = AITranscriptInterpreter()
    interpreter._transcript_to_steps_skill = StubTranscriptSkill()
    interpreter.is_enabled = lambda: True

    result = interpreter.interpret(transcript_artifact_id="artifact-1", transcript_text="00:00:05 Open vendor transaction")

    assert result is not None
    assert result.steps[0]["application_name"] == "SAP"
    assert result.steps[0]["timestamp"] == "00:00:05"
    assert result.notes[0]["text"] == "Vendor must exist"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest worker/tests/test_transcript_to_steps_skill.py::test_interpret_uses_transcript_skill_and_preserves_legacy_shape -v`

Expected: FAIL because the interpreter does not yet delegate to the skill.

- [ ] **Step 3: Update the interpreter to delegate transcript-to-steps**

In `worker/services/ai_transcript_interpreter.py`, make these focused changes:

1. import the new request/response types and skill
2. create `self._transcript_to_steps_skill` in `__init__`
3. replace the current hardcoded `interpret(...)` model-call block with skill delegation
4. add a small adapter method that converts `TranscriptToStepsResponse` into the current legacy `TranscriptInterpretation`

Target shape:

```python
from worker.services.ai_skills.transcript_to_steps.schemas import TranscriptToStepsRequest, TranscriptToStepsResponse
from worker.services.ai_skills.transcript_to_steps.skill import TranscriptToStepsSkill


class AITranscriptInterpreter:
    def __init__(self) -> None:
        self.settings = get_backend_settings()
        self._transcript_to_steps_skill = TranscriptToStepsSkill()

    def interpret(self, *, transcript_artifact_id: str, transcript_text: str) -> TranscriptInterpretation | None:
        if not self.is_enabled():
            return None

        skill_result = self._transcript_to_steps_skill.run(
            TranscriptToStepsRequest(
                transcript_artifact_id=transcript_artifact_id,
                transcript_text=transcript_text,
            )
        )
        return self._build_legacy_transcript_interpretation(
            transcript_artifact_id=transcript_artifact_id,
            skill_result=skill_result,
        )
```

Adapter method target:

```python
def _build_legacy_transcript_interpretation(
    self,
    *,
    transcript_artifact_id: str,
    skill_result: TranscriptToStepsResponse,
) -> TranscriptInterpretation:
    steps = [
        self._normalize_step(
            {
                "application_name": item.application_name,
                "action_text": item.action_text,
                "source_data_note": item.source_data_note,
                "start_timestamp": item.start_timestamp,
                "end_timestamp": item.end_timestamp,
                "display_timestamp": item.display_timestamp,
                "supporting_transcript_text": item.supporting_transcript_text,
                "confidence": item.confidence,
            },
            transcript_artifact_id,
        )
        for item in skill_result.steps
    ]
    notes = [
        self._normalize_note(
            {
                "text": item.text,
                "confidence": item.confidence,
                "inference_type": item.inference_type,
            }
        )
        for item in skill_result.notes
    ]
    return TranscriptInterpretation(steps=steps, notes=notes)
```

- [ ] **Step 4: Run tests to verify compatibility**

Run: `pytest worker/tests/test_transcript_to_steps_skill.py -v`

Expected: PASS, including the interpreter compatibility test.

- [ ] **Step 5: Commit**

```bash
git add worker/tests/test_transcript_to_steps_skill.py worker/services/ai_transcript_interpreter.py
git commit -m "Delegate transcript interpretation to AI skill"
```

---

### Task 8: Register The First Skill And Cover Registry Wiring

**Files:**
- Modify: `worker/services/ai_skills/registry.py`
- Modify: `worker/tests/test_ai_skill_runtime.py`
- Create optionally if needed: `worker/services/ai_skills/__init__.py`

- [ ] **Step 1: Write the failing test for default transcript skill registration**

Add to `worker/tests/test_ai_skill_runtime.py`:

```python
from worker.services.ai_skills.registry import build_default_ai_skill_registry


def test_default_registry_includes_transcript_to_steps_skill() -> None:
    registry = build_default_ai_skill_registry()

    skill = registry.create("transcript_to_steps")

    assert skill.skill_id == "transcript_to_steps"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest worker/tests/test_ai_skill_runtime.py -v`

Expected: FAIL because the builder function does not exist yet.

- [ ] **Step 3: Add the default skill-registration helper**

Update `worker/services/ai_skills/registry.py`:

```python
from worker.services.ai_skills.transcript_to_steps.skill import TranscriptToStepsSkill


def build_default_ai_skill_registry() -> AISkillRegistry:
    registry = AISkillRegistry()
    registry.register("transcript_to_steps", TranscriptToStepsSkill)
    return registry
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest worker/tests/test_ai_skill_runtime.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add worker/tests/test_ai_skill_runtime.py worker/services/ai_skills/registry.py
git commit -m "Register transcript-to-steps AI skill"
```

---

### Task 9: Run Regression Tests For The Worker Slice

**Files:**
- Test: `worker/tests/test_transcript_to_steps_skill.py`
- Test: `worker/tests/test_ai_skill_runtime.py`
- Test: `worker/tests/test_draft_generation_worker.py`

- [ ] **Step 1: Run focused new tests**

Run: `pytest worker/tests/test_ai_skill_runtime.py worker/tests/test_transcript_to_steps_skill.py -v`

Expected: PASS.

- [ ] **Step 2: Run existing worker regression coverage**

Run: `pytest worker/tests/test_draft_generation_worker.py -v`

Expected: PASS, or else identify and fix any compatibility regressions before proceeding.

- [ ] **Step 3: Run the combined worker slice**

Run: `pytest worker/tests/test_ai_skill_runtime.py worker/tests/test_transcript_to_steps_skill.py worker/tests/test_draft_generation_worker.py -v`

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add worker/tests/test_draft_generation_worker.py
git commit -m "Verify hybrid AI skill worker regression coverage"
```

---

### Task 10: Final Cleanup And Documentation Verification

**Files:**
- Verify: `docs/superpowers/specs/2026-04-02-hybrid-ai-skills-design.md`
- Verify: `docs/superpowers/plans/2026-04-02-hybrid-ai-skills-implementation.md`
- Verify: `worker/services/ai_skills/transcript_to_steps/SKILL.md`
- Verify: `worker/services/ai_skills/transcript_to_steps/prompt.md`

- [ ] **Step 1: Verify the new framework tree exists**

Run: `Get-ChildItem -Recurse worker\\services\\ai_skills`

Expected: shows `base.py`, `client.py`, `registry.py`, `runtime.py`, and the `transcript_to_steps` skill directory with markdown and Python files.

- [ ] **Step 2: Verify the working tree is clean except for intended plan/spec artifacts**

Run: `git status --short`

Expected: empty output before final commit, or only intended files if this step is being performed mid-task.

- [ ] **Step 3: Commit any final doc or cleanup changes**

```bash
git add worker/services/ai_skills worker/services/ai_transcript_interpreter.py worker/tests/test_ai_skill_runtime.py worker/tests/test_transcript_to_steps_skill.py worker/tests/test_draft_generation_worker.py
git commit -m "Complete first hybrid AI skill migration"
```

---

## Self-Review

### Spec coverage

- hybrid framework added:
  - covered by Tasks 1, 2, 3, and 8
- markdown + Python split:
  - covered by Tasks 4, 5, and 6
- first migrated `transcript_to_steps` skill:
  - covered by Tasks 4, 5, 6, and 7
- compatibility facade in old interpreter:
  - covered by Task 7
- regression verification:
  - covered by Task 9

No uncovered spec requirements remain for this branch-sized scope.

### Placeholder scan

The plan contains:

- exact file paths
- explicit test code
- explicit implementation snippets
- concrete commands

No `TODO`, `TBD`, or deferred placeholders remain.

### Type consistency

The plan uses these consistent names throughout:

- `AISkill`
- `AISkillRegistry`
- `TranscriptToStepsRequest`
- `TranscriptToStepsResponse`
- `TranscriptStep`
- `TranscriptNote`
- `TranscriptToStepsSkill`

These names remain consistent across tests, implementation tasks, and compatibility wiring.
