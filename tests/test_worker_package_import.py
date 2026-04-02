from __future__ import annotations

import importlib
import unittest


class WorkerPackageImportTests(unittest.TestCase):
    def test_import_worker_package_without_bootstrap_side_effects(self) -> None:
        module = importlib.import_module("worker")

        self.assertEqual(module.__name__, "worker")
