from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from app.core.config import Settings
from app.portability.job_messaging.envelope import JobEnvelope, JobType
from app.portability.job_messaging.enqueue_producers.azure_service_bus_enqueue import AzureServiceBusJobEnqueueAdapter
from app.portability.job_messaging.enqueue_producers.celery_enqueue import CeleryJobEnqueueAdapter
from app.portability.job_messaging.enqueue_producers.gcp_pubsub_enqueue import GcpPubSubJobEnqueueAdapter
from app.portability.job_messaging.enqueue_producers.sqs_enqueue import SqsJobEnqueueAdapter


class JobEnqueueProducerAdapterTests(unittest.TestCase):
    @patch("app.portability.job_messaging.enqueue_producers.sqs_enqueue.boto3.client")
    def test_sqs_uses_logical_queue_mapping(self, mock_client_factory: MagicMock) -> None:
        mock_client = MagicMock()
        mock_client.send_message.return_value = {"MessageId": "msg-1"}
        mock_client_factory.return_value = mock_client
        settings = Settings(
            database_url="postgresql+psycopg://x:x@localhost:5432/x",
            job_enqueue_backend="sqs",
            sqs_job_queue_urls={"draft-generation": "https://example.local/draft"},
        )
        adapter = SqsJobEnqueueAdapter(settings=settings)
        handle = adapter.enqueue(
            JobEnvelope(job_type=JobType.DRAFT_GENERATION, session_id="s-1"),
            queue="draft-generation",
        )
        self.assertEqual(handle.id, "msg-1")
        mock_client.send_message.assert_called_once()
        kwargs = mock_client.send_message.call_args.kwargs
        self.assertEqual(kwargs["QueueUrl"], "https://example.local/draft")

    def test_celery_retries_once_then_succeeds(self) -> None:
        celery_app = MagicMock()
        result = MagicMock()
        result.id = "celery-1"
        celery_app.send_task.side_effect = [RuntimeError("temporary"), result]
        adapter = CeleryJobEnqueueAdapter(celery_app=celery_app, max_retries=1, retry_backoff_seconds=0.0)
        handle = adapter.enqueue(
            JobEnvelope(job_type=JobType.SCREENSHOT_GENERATION, session_id="s-2"),
            queue="draft-generation",
        )
        self.assertEqual(handle.id, "celery-1")
        self.assertEqual(celery_app.send_task.call_count, 2)

    @patch("app.portability.job_messaging.enqueue_producers.azure_service_bus_enqueue.ServiceBusClient")
    def test_azure_uses_logical_queue_mapping(self, mock_client_cls: MagicMock) -> None:
        sender = MagicMock()
        sender.__enter__.return_value = sender
        sender.__exit__.return_value = False
        client = MagicMock()
        client.__enter__.return_value = client
        client.__exit__.return_value = False
        client.get_queue_sender.return_value = sender
        mock_client_cls.from_connection_string.return_value = client
        settings = Settings(
            database_url="postgresql+psycopg://x:x@localhost:5432/x",
            job_enqueue_backend="azure_service_bus",
            azure_service_bus_connection_string="Endpoint=sb://x/",
            azure_service_bus_queue_names={"draft-generation": "draft-queue"},
        )
        adapter = AzureServiceBusJobEnqueueAdapter(settings=settings)
        adapter.enqueue(
            JobEnvelope(job_type=JobType.DRAFT_GENERATION, session_id="s-3"),
            queue="draft-generation",
        )
        client.get_queue_sender.assert_called_once_with(queue_name="draft-queue")
        sender.send_messages.assert_called_once()

    @patch("app.portability.job_messaging.enqueue_producers.gcp_pubsub_enqueue.pubsub_v1.PublisherClient")
    def test_gcp_uses_logical_queue_mapping(self, mock_pub_cls: MagicMock) -> None:
        publisher = MagicMock()
        publisher.topic_path.side_effect = lambda project, topic: f"projects/{project}/topics/{topic}"
        future = MagicMock()
        future.result.return_value = "pub-1"
        publisher.publish.return_value = future
        mock_pub_cls.return_value = publisher
        settings = Settings(
            database_url="postgresql+psycopg://x:x@localhost:5432/x",
            job_enqueue_backend="gcp_pubsub",
            gcp_pubsub_project_id="my-project",
            gcp_pubsub_topic_ids={"draft-generation": "draft-topic"},
        )
        adapter = GcpPubSubJobEnqueueAdapter(settings=settings)
        handle = adapter.enqueue(
            JobEnvelope(job_type=JobType.DRAFT_GENERATION, session_id="s-4"),
            queue="draft-generation",
        )
        self.assertEqual(handle.id, "pub-1")
        publisher.publish.assert_called_once()
        args = publisher.publish.call_args.args
        self.assertEqual(args[0], "projects/my-project/topics/draft-topic")


if __name__ == "__main__":
    unittest.main()
