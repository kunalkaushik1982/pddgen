"""Shared sys.modules cleanup so integration tests load real app/sqlalchemy after stub-heavy tests."""

from __future__ import annotations

import importlib
import sys


def clear_stub_modules_for_integration_tests() -> None:
    app_keys = [k for k in list(sys.modules) if k == "app" or k.startswith("app.")]
    app_keys.sort(key=len, reverse=True)
    for key in app_keys:
        mod = sys.modules.get(key)
        if mod is None:
            continue
        if getattr(mod, "__path__", None):
            continue
        sys.modules.pop(key, None)
    worker_pkg = sys.modules.get("worker")
    if worker_pkg is not None:
        paths = list(getattr(worker_pkg, "__path__", ()) or ())
        if len(paths) == 0:
            for key in list(sys.modules):
                if key.startswith("worker.tests"):
                    continue
                if key == "worker" or key.startswith("worker."):
                    sys.modules.pop(key, None)
    sys.modules.pop("worker.bootstrap", None)
    sa = sys.modules.get("sqlalchemy")
    if sa is not None and not hasattr(sa, "select"):
        for key in list(sys.modules):
            if key == "sqlalchemy" or key.startswith("sqlalchemy."):
                sys.modules.pop(key, None)
    for key in list(sys.modules):
        if key.startswith("worker.pipeline."):
            sys.modules.pop(key, None)
    importlib.invalidate_caches()
    importlib.import_module("app")
    importlib.import_module("worker")
