r"""Google Cloud Pub/Sub producer implementing `JobEnqueuePort` (JSON `JobEnvelope` as message data)."""

from __future__ import annotations

from google.cloud import pubsub_v1

from app.core.config import Settings
from app.portability.job_messaging.enqueue_producers.common import resolve_target_for_queue, send_with_retry
from app.portability.job_messaging.envelope import JobEnvelope
from app.portability.job_messaging.protocols import EnqueueHandle, JobEnqueuePort


class _GcpPubSubEnqueueHandle:
    __slots__ = ("_id",)

    def __init__(self, message_id: str) -> None:
        self._id = message_id

    @property
    def id(self) -> str:
        return self._id


class GcpPubSubJobEnqueueAdapter(JobEnqueuePort):
    """Publish to Pub/Sub with logical queue -> topic-id mapping support."""

    __slots__ = ("_publisher", "_project", "_topic_id", "_topic_ids", "_max_retries", "_retry_backoff")

    def __init__(self, *, settings: Settings) -> None:
        self._project = settings.gcp_pubsub_project_id.strip()
        self._topic_id = settings.gcp_pubsub_topic_id.strip()
        self._topic_ids = dict(settings.gcp_pubsub_topic_ids)
        self._max_retries = settings.job_enqueue_max_retries
        self._retry_backoff = settings.job_enqueue_retry_backoff_seconds
        self._publisher = pubsub_v1.PublisherClient()

    def enqueue(self, job: JobEnvelope, *, queue: str) -> EnqueueHandle:
        topic_id = resolve_target_for_queue(
            queue=queue,
            mapping=self._topic_ids,
            fallback=self._topic_id,
            target_name="gcp pubsub topic id",
        )
        topic_path = self._publisher.topic_path(self._project, topic_id)

        def _send_once() -> EnqueueHandle:
            data = job.model_dump_json().encode("utf-8")
            future = self._publisher.publish(topic_path, data=data)
            message_id = future.result()
            if isinstance(message_id, bytes):
                message_id = message_id.decode("utf-8")
            return _GcpPubSubEnqueueHandle(str(message_id))

        return send_with_retry(
            backend="gcp_pubsub",
            queue=queue,
            job=job,
            max_retries=self._max_retries,
            backoff_seconds=self._retry_backoff,
            send_once=_send_once,
        )
