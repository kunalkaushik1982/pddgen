# Job Messaging Producer: Why and How

This document explains why we introduced the new queue-producer architecture, what is implemented now, and how to extend it with plug-in style providers using a dotted import path.

## Why We Are Doing This

Previously, queueing logic was tightly coupled to a single backend pattern. That makes customer onboarding harder when each customer has different infrastructure preferences (Redis/Celery, AWS SQS, Azure Service Bus, GCP Pub/Sub, etc.).

Goals of the new design:

- Decouple application logic from queue technology.
- Keep one stable producer contract in backend services.
- Switch between built-in providers using config, not business-code edits.
- Allow custom provider plug-ins via dotted import path (`module.path:callable`).
- Keep future provider additions low-touch and safer to review.

## What Is Implemented

### 1) Stable producer port

The backend uses a single contract:

- `JobEnqueuePort` in `backend/app/portability/job_messaging/protocols.py`
- Method: `enqueue(job: JobEnvelope, *, queue: str) -> EnqueueHandle`

This means service code (for example `JobDispatcherService`) does not care whether the adapter uses Celery, SQS, Azure Service Bus, or Pub/Sub.

### 2) Typed message model

`JobEnvelope` in `backend/app/portability/job_messaging/envelope.py` standardizes the producer payload:

- `version`
- `job_type`
- `session_id`

This keeps queue payloads explicit and versionable.

### 3) Built-in producer adapters

Current built-ins under `backend/app/portability/job_messaging/enqueue_producers/`:

- `celery_enqueue.py`
- `sqs_enqueue.py`
- `azure_service_bus_enqueue.py`
- `gcp_pubsub_enqueue.py`

These are selected by `job_enqueue_backend` unless a plug-in factory is configured.

### 4) Registry + optional plug-in factory

`backend/app/portability/job_messaging/wiring.py` now supports:

- Built-in registry lookup (`job_enqueue_backend`)
- Optional override via `job_enqueue_factory` (dotted import path)

If `job_enqueue_factory` is set, it takes precedence over built-in backend selection.

## Config Surface

All settings are in `backend/app/core/config.py` and `backend/.env.example`.

### Built-in selection

- `PDD_GENERATOR_JOB_ENQUEUE_BACKEND=celery|sqs|azure_service_bus|gcp_pubsub`

Provider-specific fields (examples):

- SQS: `PDD_GENERATOR_SQS_JOB_QUEUE_URL`, `PDD_GENERATOR_SQS_REGION`, `PDD_GENERATOR_SQS_IS_FIFO_QUEUE`
- Azure Service Bus: `PDD_GENERATOR_AZURE_SERVICE_BUS_CONNECTION_STRING`, `PDD_GENERATOR_AZURE_SERVICE_BUS_QUEUE_NAME`
- GCP Pub/Sub: `PDD_GENERATOR_GCP_PUBSUB_PROJECT_ID`, `PDD_GENERATOR_GCP_PUBSUB_TOPIC_ID`
- Optional logical queue mappings:
  - `PDD_GENERATOR_SQS_JOB_QUEUE_URLS` (JSON dict)
  - `PDD_GENERATOR_AZURE_SERVICE_BUS_QUEUE_NAMES` (JSON dict)
  - `PDD_GENERATOR_GCP_PUBSUB_TOPIC_IDS` (JSON dict)
- Producer retry policy:
  - `PDD_GENERATOR_JOB_ENQUEUE_MAX_RETRIES`
  - `PDD_GENERATOR_JOB_ENQUEUE_RETRY_BACKOFF_SECONDS`

### Plug-in selection (override)

- `PDD_GENERATOR_JOB_ENQUEUE_FACTORY=module.path:callable`

Example:

```env
PDD_GENERATOR_JOB_ENQUEUE_FACTORY=company_platform.messaging.azure:build_enqueue_port
```

Expected callable signature:

```python
def build_enqueue_port(settings: Settings) -> JobEnqueuePort:
    ...
```

## How Runtime Resolution Works

`build_job_enqueue_port(settings)` resolves producers in this order:

1. If `job_enqueue_factory` is set:
   - Parse `module.path:callable`
   - Import module via `importlib`
   - Load attribute and verify it is callable
   - Call it with `settings`
2. Else:
   - Use built-in registry based on `job_enqueue_backend`

The dotted factory resolver is cached with `lru_cache` for repeated use.

## Validation Behavior

`Settings.validate_job_enqueue_backend()` enforces:

- If `job_enqueue_factory` is provided:
  - Must be exactly `module.path:callable`
  - Built-in provider field validation is skipped (plugin owns its config)
- Else:
  - Built-in provider-specific required fields are validated

## How To Add a New Provider (No Core Wiring Change)

Use plug-in factory mode.

1. Create your module (inside repo or installed package), for example:
   - `company_platform/messaging/kafka_enqueue.py`
2. Implement:
   - A class implementing `JobEnqueuePort`
   - A builder callable `(settings) -> JobEnqueuePort`
3. Set:
   - `PDD_GENERATOR_JOB_ENQUEUE_FACTORY=company_platform.messaging.kafka_enqueue:build_enqueue_port`
4. Restart backend.

No changes are required in `wiring.py` for this path.

## Copy-Paste Plug-in Templates

These examples show the exact shape expected by `job_enqueue_factory`. Replace module names and settings fields as needed.

### 1) Azure Service Bus plugin template

```python
from __future__ import annotations

import uuid
from azure.servicebus import ServiceBusClient, ServiceBusMessage

from app.core.config import Settings
from app.portability.job_messaging.envelope import JobEnvelope
from app.portability.job_messaging.protocols import EnqueueHandle, JobEnqueuePort


class _Handle:
    def __init__(self, message_id: str) -> None:
        self._id = message_id

    @property
    def id(self) -> str:
        return self._id


class AzureServiceBusPluginAdapter(JobEnqueuePort):
    def __init__(self, *, connection_string: str, queue_name: str) -> None:
        self._connection_string = connection_string
        self._queue_name = queue_name

    def enqueue(self, job: JobEnvelope, *, queue: str) -> EnqueueHandle:
        _ = queue
        body = job.model_dump_json().encode("utf-8")
        message_id = str(uuid.uuid4())
        message = ServiceBusMessage(body, message_id=message_id, content_type="application/json")
        with ServiceBusClient.from_connection_string(self._connection_string) as client:
            with client.get_queue_sender(queue_name=self._queue_name) as sender:
                sender.send_messages(message)
        return _Handle(message_id)


def build_enqueue_port(settings: Settings) -> JobEnqueuePort:
    # Use your own config names if needed.
    return AzureServiceBusPluginAdapter(
        connection_string=settings.azure_service_bus_connection_string,
        queue_name=settings.azure_service_bus_queue_name,
    )
```

Set:

```env
PDD_GENERATOR_JOB_ENQUEUE_FACTORY=company_platform.messaging.azure_plugin:build_enqueue_port
```

### 2) GCP Pub/Sub plugin template

```python
from __future__ import annotations

from google.cloud import pubsub_v1

from app.core.config import Settings
from app.portability.job_messaging.envelope import JobEnvelope
from app.portability.job_messaging.protocols import EnqueueHandle, JobEnqueuePort


class _Handle:
    def __init__(self, message_id: str) -> None:
        self._id = message_id

    @property
    def id(self) -> str:
        return self._id


class GcpPubSubPluginAdapter(JobEnqueuePort):
    def __init__(self, *, project_id: str, topic_id: str) -> None:
        self._publisher = pubsub_v1.PublisherClient()
        self._topic_path = self._publisher.topic_path(project_id, topic_id)

    def enqueue(self, job: JobEnvelope, *, queue: str) -> EnqueueHandle:
        _ = queue
        data = job.model_dump_json().encode("utf-8")
        future = self._publisher.publish(self._topic_path, data=data)
        message_id = future.result()
        if isinstance(message_id, bytes):
            message_id = message_id.decode("utf-8")
        return _Handle(str(message_id))


def build_enqueue_port(settings: Settings) -> JobEnqueuePort:
    return GcpPubSubPluginAdapter(
        project_id=settings.gcp_pubsub_project_id,
        topic_id=settings.gcp_pubsub_topic_id,
    )
```

Set:

```env
PDD_GENERATOR_JOB_ENQUEUE_FACTORY=company_platform.messaging.gcp_plugin:build_enqueue_port
```

### 3) Generic HTTP/webhook plugin template

Useful when customer infrastructure exposes an internal queue gateway API.

```python
from __future__ import annotations

import httpx

from app.core.config import Settings
from app.portability.job_messaging.envelope import JobEnvelope
from app.portability.job_messaging.protocols import EnqueueHandle, JobEnqueuePort


class _Handle:
    def __init__(self, request_id: str) -> None:
        self._id = request_id

    @property
    def id(self) -> str:
        return self._id


class HttpQueueGatewayAdapter(JobEnqueuePort):
    def __init__(self, *, base_url: str, token: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = token

    def enqueue(self, job: JobEnvelope, *, queue: str) -> EnqueueHandle:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                f"{self._base_url}/enqueue",
                json={"queue": queue, "job": job.model_dump(mode="json")},
                headers={"Authorization": f"Bearer {self._token}"},
            )
            response.raise_for_status()
            payload = response.json()
        return _Handle(str(payload.get("id", "unknown")))


def build_enqueue_port(settings: Settings) -> JobEnqueuePort:
    # Replace with your own env-backed settings field names.
    return HttpQueueGatewayAdapter(
        base_url=settings.ai_base_url,
        token=settings.ai_api_key,
    )
```

Set:

```env
PDD_GENERATOR_JOB_ENQUEUE_FACTORY=company_platform.messaging.http_queue:build_enqueue_port
```

## When To Use Built-ins vs Plug-in Factory

- Use built-ins when provider is standard and maintained in this repo.
- Use `job_enqueue_factory` when:
  - Customer requires proprietary queue wrapper.
  - You want provider-specific logic without touching shared core.
  - You need temporary migration adapters.

## Security and Operational Notes

- Treat `job_enqueue_factory` as trusted input only.
  - It imports Python modules from a string path.
  - Do not allow untrusted users to set this env var.
- This document covers producer-side only.
  - Non-Celery producers still require corresponding consumers for end-to-end processing.
- Keep provider credentials in secure secret stores, not committed `.env` files.

## Related Files

- Port contract: `backend/app/portability/job_messaging/protocols.py`
- Message model: `backend/app/portability/job_messaging/envelope.py`
- Producer wiring: `backend/app/portability/job_messaging/wiring.py`
- Built-in adapters: `backend/app/portability/job_messaging/enqueue_producers/`
- Settings and validation: `backend/app/core/config.py`
- Example envs: `backend/.env.example`
