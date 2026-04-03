from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

try:
    from worker.services.workflow_intelligence.grouping_service import *  # type: ignore[F403]
except ModuleNotFoundError:
    _GENERATION_TYPES_MODULE = "worker.services.generation_types"
    if _GENERATION_TYPES_MODULE not in sys.modules:
        _GENERATION_TYPES_PATH = Path(__file__).resolve().parent / "generation_types.py"
        _GENERATION_TYPES_SPEC = importlib.util.spec_from_file_location(_GENERATION_TYPES_MODULE, _GENERATION_TYPES_PATH)
        if _GENERATION_TYPES_SPEC is None or _GENERATION_TYPES_SPEC.loader is None:
            raise RuntimeError(f"Unable to load compatibility module from {_GENERATION_TYPES_PATH}.")
        _GENERATION_TYPES = importlib.util.module_from_spec(_GENERATION_TYPES_SPEC)
        sys.modules[_GENERATION_TYPES_MODULE] = _GENERATION_TYPES
        _GENERATION_TYPES_SPEC.loader.exec_module(_GENERATION_TYPES)

    _MODULE_PATH = Path(__file__).resolve().parent / "workflow_intelligence" / "grouping_service.py"
    _SPEC = importlib.util.spec_from_file_location("_worker_services_workflow_grouping_service", _MODULE_PATH)
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
