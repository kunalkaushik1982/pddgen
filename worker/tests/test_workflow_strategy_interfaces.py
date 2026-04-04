from __future__ import annotations

import ast
from pathlib import Path
import unittest


MODULE_PATH = Path(__file__).resolve().parents[1] / "grouping" / "strategy_interfaces.py"


class WorkflowStrategyInterfacesTests(unittest.TestCase):
    def test_protocol_methods_use_ellipsis_stubs(self) -> None:
        module = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
        expected_methods = {
            "TranscriptSegmentationStrategy": {"segment"},
            "SegmentEnrichmentStrategy": {"enrich"},
            "WorkflowBoundaryStrategy": {"decide"},
        }

        for node in module.body:
            if not isinstance(node, ast.ClassDef) or node.name not in expected_methods:
                continue
            for item in node.body:
                if not isinstance(item, ast.FunctionDef) or item.name not in expected_methods[node.name]:
                    continue
                self.assertGreaterEqual(len(item.body), 2)
                self.assertIsInstance(item.body[-1], ast.Expr)
                self.assertIsInstance(item.body[-1].value, ast.Constant)
                self.assertEqual(item.body[-1].value.value, Ellipsis)


if __name__ == "__main__":
    unittest.main()
