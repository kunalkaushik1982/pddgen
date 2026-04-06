r"""SQS-backed `JobEnqueuePort` (producer sends JSON `JobEnvelope` bodies)."""

from __future__ import annotations

import uuid

import boto3

from app.core.config import Settings
from app.portability.job_messaging.envelope import JobEnvelope
from app.portability.job_messaging.protocols import EnqueueHandle, JobEnqueuePort


class _SqsEnqueueHandle:
    __slots__ = ("_id",)

    def __init__(self, message_id: str) -> None:
        self._id = message_id

    @property
    def id(self) -> str:
        return self._id


class SqsJobEnqueueAdapter(JobEnqueuePort):
    """`SendMessage` with envelope JSON. Single-queue URL from settings; `queue` name is ignored until multi-queue mapping exists."""

    __slots__ = ("_client", "_settings", "_queue_url")

    def __init__(self, *, settings: Settings) -> None:
        self._settings = settings
        region = settings.sqs_region.strip() if settings.sqs_region else None
        self._client = boto3.client("sqs", region_name=region or None)
        self._queue_url = settings.sqs_job_queue_url.strip()

    def enqueue(self, job: JobEnvelope, *, queue: str) -> EnqueueHandle:
        _ = queue
        body = job.model_dump_json()
        params: dict[str, str] = {"QueueUrl": self._queue_url, "MessageBody": body}
        if self._settings.sqs_is_fifo_queue:
            params["MessageGroupId"] = job.session_id[:128]
            params["MessageDeduplicationId"] = str(uuid.uuid4())
        resp = self._client.send_message(**params)
        return _SqsEnqueueHandle(resp["MessageId"])
