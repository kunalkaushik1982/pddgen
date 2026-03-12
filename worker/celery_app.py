r"""
Purpose: Celery application configuration for background processing.
Full filepath: C:\Users\work\Documents\PddGenerator\worker\celery_app.py
"""

import sys

from celery import Celery

from worker.bootstrap import get_backend_settings


def create_celery_app() -> Celery:
    """Create the Celery application."""
    settings = get_backend_settings()
    app = Celery(
        "pdd_generator",
        broker=settings.redis_url,
        backend=settings.redis_url,
        include=["worker.tasks.draft_generation"],
    )
    app.conf.update(
        task_default_queue="draft-generation",
        task_track_started=True,
        worker_prefetch_multiplier=1,
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        broker_connection_retry_on_startup=True,
    )
    if sys.platform.startswith("win"):
        # Celery's default prefork pool is unreliable on Windows. Use solo for local development.
        app.conf.worker_pool = "solo"
    return app


celery_app = create_celery_app()
