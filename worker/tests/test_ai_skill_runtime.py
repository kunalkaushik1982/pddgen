from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

RUNTIME_PATH = Path(__file__).resolve().parents[1] / "services" / "ai_skills" / "runtime.py"
BASE_PATH = Path(__file__).resolve().parents[1] / "services" / "ai_skills" / "base.py"
REGISTRY_PATH = Path(__file__).resolve().parents[1] / "services" / "ai_skills" / "registry.py"
CLIENT_PATH = Path(__file__).resolve().parents[1] / "services" / "ai_skills" / "client.py"


def load_runtime_module():
    spec = importlib.util.spec_from_file_location("ai_skill_runtime", RUNTIME_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_base_module():
    spec = importlib.util.spec_from_file_location("ai_skill_base", BASE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_registry_module():
    spec = importlib.util.spec_from_file_location("ai_skill_registry", REGISTRY_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_client_module():
    spec = importlib.util.spec_from_file_location("ai_skill_client", CLIENT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class AiSkillRuntimeTests(unittest.TestCase):
    def test_load_markdown_text_reads_utf8_and_strips_whitespace(self) -> None:
        runtime = load_runtime_module()
        test_case = self

        class FakePath:
            def read_text(self, encoding: str) -> str:
                test_case.assertEqual(encoding, "utf-8")
                return "  \n# Prompt\n\nUse this carefully.  \n"

        self.assertEqual(runtime.load_markdown_text(FakePath()), "# Prompt\n\nUse this carefully.")

    def test_parse_json_object_accepts_fenced_json(self) -> None:
        runtime = load_runtime_module()
        parsed = runtime.parse_json_object("```json\n{\"name\": \"Alice\", \"count\": 2}\n```")

        self.assertEqual(parsed, {"name": "Alice", "count": 2})

    def test_parse_json_object_accepts_plain_json(self) -> None:
        runtime = load_runtime_module()
        parsed = runtime.parse_json_object("{\"name\": \"Alice\", \"count\": 2}")

        self.assertEqual(parsed, {"name": "Alice", "count": 2})

    def test_parse_json_object_rejects_non_object_json(self) -> None:
        runtime = load_runtime_module()
        with self.assertRaisesRegex(ValueError, "JSON object"):
            runtime.parse_json_object("[1, 2, 3]")

    def test_skill_registry_resolves_registered_skill(self) -> None:
        registry_module = load_registry_module()

        class DummySkill:
            skill_id = "dummy"
            version = "1.0"

            def run(self, input: object) -> object:
                return input

        registry = registry_module.AISkillRegistry()
        registry.register("dummy", lambda: DummySkill())
        skill = registry.create("dummy")

        self.assertEqual(skill.skill_id, "dummy")
        self.assertEqual(skill.version, "1.0")

    def test_skill_registry_rejects_unknown_skill(self) -> None:
        registry_module = load_registry_module()
        registry = registry_module.AISkillRegistry()

        with self.assertRaisesRegex(ValueError, "Unknown AI skill"):
            registry.create("missing")

    def test_extract_message_content_accepts_string_content(self) -> None:
        client_module = load_client_module()
        body = {"choices": [{"message": {"content": '{"steps": [], "notes": []}'}}]}

        self.assertEqual(client_module.extract_message_content(body), '{"steps": [], "notes": []}')

    def test_extract_message_content_accepts_list_content(self) -> None:
        client_module = load_client_module()
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

        self.assertEqual(client_module.extract_message_content(body), '{"steps": [], "notes": []}')

    def test_default_registry_includes_transcript_to_steps_skill(self) -> None:
        registry_module = load_registry_module()

        registry = registry_module.build_default_ai_skill_registry()
        skill = registry.create("transcript_to_steps")

        self.assertEqual(skill.skill_id, "transcript_to_steps")

    def test_default_registry_includes_semantic_enrichment_skill(self) -> None:
        registry_module = load_registry_module()

        registry = registry_module.build_default_ai_skill_registry()
        skill = registry.create("semantic_enrichment")

        self.assertEqual(skill.skill_id, "semantic_enrichment")

    def test_default_registry_includes_workflow_boundary_detection_skill(self) -> None:
        registry_module = load_registry_module()

        registry = registry_module.build_default_ai_skill_registry()
        skill = registry.create("workflow_boundary_detection")

        self.assertEqual(skill.skill_id, "workflow_boundary_detection")


if __name__ == "__main__":
    unittest.main()
