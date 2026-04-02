from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

SCHEMAS_PATH = (
    Path(__file__).resolve().parents[1]
    / "services"
    / "ai_skills"
    / "transcript_to_steps"
    / "schemas.py"
)


def load_schemas_module():
    spec = importlib.util.spec_from_file_location("transcript_to_steps_schemas", SCHEMAS_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class TranscriptToStepsSchemaTests(unittest.TestCase):
    def test_transcript_to_steps_response_holds_steps_and_notes(self) -> None:
        schemas = load_schemas_module()
        response = schemas.TranscriptToStepsResponse(
            steps=[
                schemas.TranscriptStep(
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
            notes=[
                schemas.TranscriptNote(
                    text="Vendor must exist first",
                    confidence="medium",
                    inference_type="inferred",
                )
            ],
        )

        self.assertEqual(response.steps[0].application_name, "SAP")
        self.assertEqual(response.notes[0].inference_type, "inferred")

    def test_transcript_to_steps_request_keeps_transcript_input(self) -> None:
        schemas = load_schemas_module()
        request = schemas.TranscriptToStepsRequest(
            transcript_artifact_id="artifact-1",
            transcript_text="00:00:01 Open SAP",
        )

        self.assertEqual(request.transcript_artifact_id, "artifact-1")
        self.assertIn("Open SAP", request.transcript_text)


if __name__ == "__main__":
    unittest.main()
