from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

RUNTIME_PATH = Path(__file__).resolve().parents[1] / "services" / "ai_skills" / "runtime.py"


def load_runtime_module():
    spec = importlib.util.spec_from_file_location("ai_skill_runtime", RUNTIME_PATH)
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


if __name__ == "__main__":
    unittest.main()
