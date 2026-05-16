"""
Smoke E2E tests — verify docker-compose stack via real HTTP.

Run from host against the running stack (reaches web/minio/jaeger via
published localhost ports). Requires `make up` first:
    make smoke

Tracing precondition: smoke + compose web + worker MUST all use
SimpleSpanProcessor → spans export synchronously on span end and are
in Jaeger immediately. This lets assertions skip force_flush() and
query Jaeger mid-span. Perf irrelevant in tests.
"""

import io
import time
import urllib.parse
from collections.abc import Iterator
from http import HTTPStatus

import pytest
import requests
from django.conf import settings
from django.urls import reverse
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from PIL import Image as PILImage

from images.models import Image, ImageStatus
from images.storage import internal_s3
from images.tests.jaeger import jaeger_client

BASE_URL = settings.SMOKE_DJANGO_WEB_URL
OTLP_ENDPOINT = settings.OTEL_EXPORTER_OTLP_ENDPOINT
SMOKE_SERVICE_NAME = settings.SMOKE_OTEL_SERVICE_NAME

POLL_MAX = 20
POLL_INTERVAL = 2
USERNAME, PASSWORD = settings.TEST_USERS[0]

pytestmark = [pytest.mark.smoke]

tracer = trace.get_tracer(__name__)


@pytest.fixture(scope="session", autouse=True)
def _smoke_tracing() -> Iterator[None]:
    """Wire OTel in the smoke test process so requests calls emit client spans
    into Jaeger and propagate traceparent headers to the Django web service."""
    resource = Resource.create({"service.name": SMOKE_SERVICE_NAME})
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(
        SimpleSpanProcessor(OTLPSpanExporter(endpoint=OTLP_ENDPOINT, insecure=True))
    )
    trace.set_tracer_provider(provider)
    RequestsInstrumentor().instrument()
    yield
    RequestsInstrumentor().uninstrument()
    provider.shutdown()


def _jpeg_bytes() -> bytes:
    buf = io.BytesIO()
    PILImage.new("RGB", (800, 600), color=(70, 130, 180)).save(buf, format="JPEG")
    return buf.getvalue()


class TestImageThumbnailFlow:
    login_viewname = "auth-login"
    images_viewname = "images-list"
    tasks_viewname = "tasks-create"
    task_detail_viewname = "tasks-detail"

    event_async_worker_verified = "infra.async_worker.verified"
    event_storage_verified = "infra.storage.verified"
    event_observability_verified = "infra.observability.verified"

    def test_create_image_and_thumbnail(self) -> None:
        with tracer.start_as_current_span("smoke.create_image_and_thumbnail") as span:
            trace_id = format(span.get_span_context().trace_id, "032x")
            session = requests.Session()
            csrf_headers = self._login(session)
            image_id, upload_url = self._create_image(session, csrf_headers)
            self._upload_to_s3(upload_url)
            task_id = self._trigger_task(session, csrf_headers, image_id)

            # infra slices: each helper verifies a distinct layer of the stack
            self._assert_async_worker_processes_task(session, task_id)
            span.add_event(self.event_async_worker_verified)

            self._assert_storage_contains_thumbnail(upload_url)
            span.add_event(self.event_storage_verified)

            self._assert_services_in_trace(trace_id)
            span.add_event(self.event_observability_verified)

        self._assert_events_in_trace(trace_id)

    def _login(self, session: requests.Session) -> dict[str, str]:
        resp = session.post(
            f"{BASE_URL}{reverse(self.login_viewname)}",
            json={"username": USERNAME, "password": PASSWORD},
            timeout=10,
        )
        assert resp.status_code == HTTPStatus.OK, f"login failed: {resp.text}"
        csrf_token = session.cookies.get("csrftoken")
        assert csrf_token, "csrftoken cookie missing after login"
        return {"X-CSRFToken": csrf_token, "Referer": BASE_URL}

    def _create_image(
        self, session: requests.Session, csrf_headers: dict[str, str]
    ) -> tuple[str, str]:
        resp = session.post(
            f"{BASE_URL}{reverse(self.images_viewname)}",
            json={"filename": "smoke_test.jpg"},
            headers=csrf_headers,
            timeout=10,
        )
        assert resp.status_code == HTTPStatus.CREATED, f"create image failed: {resp.text}"
        data = resp.json()
        assert data["upload_url"], "upload_url missing"
        return data["image_id"], data["upload_url"]

    def _upload_to_s3(self, upload_url: str) -> None:
        resp = requests.put(upload_url, data=_jpeg_bytes(), timeout=10)
        assert resp.status_code in (HTTPStatus.OK, HTTPStatus.NO_CONTENT), (
            f"upload to presigned URL failed: {resp.status_code} {resp.text}"
        )

    def _trigger_task(
        self,
        session: requests.Session,
        csrf_headers: dict[str, str],
        image_id: str,
    ) -> str:
        resp = session.post(
            f"{BASE_URL}{reverse(self.tasks_viewname)}",
            json={"image_id": image_id},
            headers=csrf_headers,
            timeout=10,
        )
        assert resp.status_code == HTTPStatus.CREATED, f"create task failed: {resp.text}"
        return resp.json()["task_id"]

    def _assert_async_worker_processes_task(self, session: requests.Session, task_id: str) -> None:
        status = "unknown"
        for _ in range(POLL_MAX):
            resp = session.get(
                f"{BASE_URL}{reverse(self.task_detail_viewname, kwargs={'task_id': task_id})}",
                timeout=10,
            )
            assert resp.status_code == HTTPStatus.OK
            status = resp.json().get("status", "unknown")
            if status == ImageStatus.DONE:
                return
            assert status != "failed", f"task failed: {resp.text}"
            time.sleep(POLL_INTERVAL)
        raise AssertionError(f"timed out waiting for task (last status={status})")

    def _assert_storage_contains_thumbnail(self, upload_url: str) -> None:
        object_key = urllib.parse.urlparse(upload_url).path.lstrip("/")
        bucket, _, original_key = object_key.partition("/")
        thumbnail_key = Image.format_thumbnail_key_from_original(original_key)
        internal_s3._client.head_object(Bucket=bucket, Key=original_key)
        internal_s3._client.head_object(Bucket=bucket, Key=thumbnail_key)

    def _assert_services_in_trace(self, trace_id: str) -> None:
        data = jaeger_client.poll_trace(trace_id)
        assert data.get("data"), f"no Jaeger trace for trace_id={trace_id}"
        service_names = jaeger_client.services_in_trace(data)
        assert {"django-thumbnail-app", "django-thumbnail-worker"} <= service_names, (
            f"missing spans. services={service_names}"
        )

    def _assert_events_in_trace(self, trace_id: str) -> None:
        data = jaeger_client.poll_trace(trace_id)
        assert data.get("data"), f"no Jaeger trace for trace_id={trace_id}"
        events = jaeger_client.extract_events(data)
        expected = {
            self.event_async_worker_verified,
            self.event_storage_verified,
            self.event_observability_verified,
        }
        assert expected <= set(events), f"missing events. events={events}"
