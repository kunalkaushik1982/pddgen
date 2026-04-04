from __future__ import annotations

import json
import types
import unittest

from worker.tests.import_cleanup import clear_stub_modules_for_integration_tests


def load_builder_module():
    clear_stub_modules_for_integration_tests()
    from worker.screenshot import context_builder

    return context_builder


class ScreenshotContextBuilderTests(unittest.TestCase):
    def test_raises_when_no_persisted_steps_exist(self) -> None:
        builder_module = load_builder_module()
        builder = builder_module.DefaultScreenshotContextBuilder()
        session = types.SimpleNamespace(
            id="session-1",
            artifacts=[types.SimpleNamespace(kind="transcript"), types.SimpleNamespace(kind="video")],
            process_steps=[],
            process_notes=[],
        )

        with self.assertRaisesRegex(ValueError, "No generated process steps"):
            builder.build(db=types.SimpleNamespace(), session=session)

    def test_removes_screenshot_evidence_and_resolves_transcript_id(self) -> None:
        builder_module = load_builder_module()
        builder = builder_module.DefaultScreenshotContextBuilder()
        step = types.SimpleNamespace(
            id="step-1",
            process_group_id="group-1",
            meeting_id="meeting-1",
            step_number=1,
            application_name="App",
            action_text="Click Save",
            source_data_note="",
            timestamp="00:00:05",
            start_timestamp="00:00:05",
            end_timestamp="00:00:06",
            supporting_transcript_text="Click Save",
            screenshot_id="old",
            confidence=0.9,
            evidence_references=json.dumps(
                [
                    {"kind": "transcript", "artifact_id": "tx-1"},
                    {"kind": "screenshot", "artifact_id": "ss-1"},
                ]
            ),
            edited_by_ba=False,
            source_transcript_artifact_id=None,
        )
        session = types.SimpleNamespace(
            id="session-1",
            artifacts=[
                types.SimpleNamespace(id="tx-1", kind="transcript", meeting_id="meeting-1", created_at=1),
                types.SimpleNamespace(id="vid-1", kind="video", meeting_id="meeting-1", created_at=1),
            ],
            process_steps=[step],
            process_notes=[],
        )
        db = types.SimpleNamespace(
            execute=lambda *args, **kwargs: None,
            commit=lambda: None,
        )

        context = builder.build(db=db, session=session)

        self.assertEqual(json.loads(step.evidence_references), [{"kind": "transcript", "artifact_id": "tx-1"}])
        self.assertEqual(context.all_steps[0]["_transcript_artifact_id"], "tx-1")
        self.assertEqual(context.persisted_step_models[0].id, "step-1")


if __name__ == "__main__":
    unittest.main()
