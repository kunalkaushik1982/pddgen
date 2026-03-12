r"""
Purpose: Inline draft-generation bridge used by backend demo mode.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\services\demo_generation_runner.py
"""

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from worker.services.draft_generation_worker import DraftGenerationWorker  # noqa: E402


class DemoGenerationRunnerService:
    """Run the worker pipeline inline for demo-only environments."""

    def run(self, session_id: str) -> dict[str, int | str]:
        """Execute the draft generation pipeline synchronously."""
        worker = DraftGenerationWorker()
        return worker.run(session_id)
