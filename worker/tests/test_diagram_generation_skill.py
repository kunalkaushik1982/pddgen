from __future__ import annotations

import unittest

from worker.ai_skills.diagram_generation.skill import normalize_diagram_view


class NormalizeDiagramViewTests(unittest.TestCase):
    def test_downgrades_linear_decision_to_process(self) -> None:
        view = {
            "title": "Vendor creation",
            "nodes": [
                {"id": "n1", "label": "Open transaction", "category": "process", "step_range": "Step 1"},
                {"id": "n2", "label": "Create vendor by entering code", "category": "decision", "step_range": "Step 2"},
                {"id": "n3", "label": "Enter vendor details", "category": "process", "step_range": "Step 3"},
            ],
            "edges": [
                {"id": "e1", "source": "n1", "target": "n2", "label": ""},
                {"id": "e2", "source": "n2", "target": "n3", "label": ""},
            ],
        }

        normalized = normalize_diagram_view(view, "detailed", "Vendor creation")

        by_id = {node["id"]: node for node in normalized["nodes"]}
        self.assertEqual(by_id["n2"]["category"], "process")

    def test_keeps_real_branching_decision(self) -> None:
        view = {
            "title": "Vendor creation",
            "nodes": [
                {"id": "n1", "label": "Check whether vendor exists", "category": "decision", "step_range": "Step 1"},
                {"id": "n2", "label": "Create vendor", "category": "process", "step_range": "Step 2"},
                {"id": "n3", "label": "Continue with account group", "category": "process", "step_range": "Step 3"},
            ],
            "edges": [
                {"id": "e1", "source": "n1", "target": "n2", "label": "No"},
                {"id": "e2", "source": "n1", "target": "n3", "label": "Yes"},
            ],
        }

        normalized = normalize_diagram_view(view, "detailed", "Vendor creation")

        by_id = {node["id"]: node for node in normalized["nodes"]}
        self.assertEqual(by_id["n1"]["category"], "decision")


if __name__ == "__main__":
    unittest.main()
