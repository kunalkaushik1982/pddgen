from __future__ import annotations

import importlib.util
from pathlib import Path

_MODULE_PATH = Path(__file__).resolve().parent / "workflow_intelligence" / "__init__.py"
_SPEC = importlib.util.spec_from_file_location("_worker_services_workflow_intelligence", _MODULE_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Unable to load compatibility module from {_MODULE_PATH}.")
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

globals().update(
    {
        name: value
        for name, value in vars(_MODULE).items()
        if not name.startswith("_")
    }
)
