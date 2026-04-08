r"""Azure Service Bus queue producer implementing `JobEnqueuePort` (JSON `JobEnvelope` body)."""

from __future__ import annotations

import uuid

from azure.servicebus import ServiceBusClient, ServiceBusMessage

from app.core.config import Settings
from app.portability.job_messaging.enqueue_producers.common import resolve_target_for_queue, send_with_retry
from app.portability.job_messaging.envelope import JobEnvelope
from app.portability.job_messaging.protocols import EnqueueHandle, JobEnqueuePort


class _AzureEnqueueHandle:
    __slots__ = ("_id",)

    def __init__(self, message_id: str) -> None:
        self._id = message_id

    @property
    def id(self) -> str:
        return self._id


class AzureServiceBusJobEnqueueAdapter(JobEnqueuePort):
    """Send to Azure Service Bus queue with logical queue -> queue-name mapping support."""

    __slots__ = ("_connection_string", "_queue_name", "_queue_names", "_max_retries", "_retry_backoff")

    def __init__(self, *, settings: Settings) -> None:
        self._connection_string = settings.azure_service_bus_connection_string.strip()
        self._queue_name = settings.azure_service_bus_queue_name.strip()
        self._queue_names = dict(settings.azure_service_bus_queue_names)
        self._max_retries = settings.job_enqueue_max_retries
        self._retry_backoff = settings.job_enqueue_retry_backoff_seconds

    def enqueue(self, job: JobEnvelope, *, queue: str) -> EnqueueHandle:
        queue_name = resolve_target_for_queue(
            queue=queue,
            mapping=self._queue_names,
            fallback=self._queue_name,
            target_name="azure service bus queue name",
        )

        def _send_once() -> EnqueueHandle:
            body = job.model_dump_json().encode("utf-8")
            message_id = str(uuid.uuid4())
            message = ServiceBusMessage(body, message_id=message_id, content_type="application/json")
            with ServiceBusClient.from_connection_string(self._connection_string) as client:
                with client.get_queue_sender(queue_name=queue_name) as sender:
                    sender.send_messages(message)
            return _AzureEnqueueHandle(message_id)

        return send_with_retry(
            backend="azure_service_bus",
            queue=queue,
            job=job,
            max_retries=self._max_retries,
            backoff_seconds=self._retry_backoff,
            send_once=_send_once,
        )
