"""
Smoke E2E tests — verify docker-compose stack via real HTTP.

Run from host against the running stack (reaches web/minio/jaeger via
published localhost ports). Requires `make up` first:
    make smoke
"""

import io
import json
import time
import urllib.parse
import urllib.request
from http import HTTPStatus

import pytest
import requests
from django.conf import settings
from django.urls import reverse
from PIL import Image as PILImage

from images.models import ImageStatus
from images.storage import internal_s3

BASE_URL = settings.SMOKE_DJANGO_WEB_URL
JAEGER_BASE = settings.SMOKE_JAEGER_BASE_URL

POLL_MAX = 20
POLL_INTERVAL = 2
USERNAME = "test1@example.com"
PASSWORD = "test1"

pytestmark = [pytest.mark.smoke]


def _jpeg_bytes() -> bytes:
    buf = io.BytesIO()
    PILImage.new("RGB", (800, 600), color=(70, 130, 180)).save(buf, format="JPEG")
    return buf.getvalue()


def _query_jaeger_trace(image_id: str) -> dict:
    tags = json.dumps({"image_id": image_id, "status": ImageStatus.DONE})
    params = urllib.parse.urlencode(
        {"service": "django-thumbnail-worker", "tags": tags, "limit": 1}
    )
    url = f"{JAEGER_BASE}/api/traces?{params}"
    with urllib.request.urlopen(url, timeout=5) as resp:
        return json.loads(resp.read())


class TestImageThumbnailFlow:
    login_viewname = "auth-login"
    images_viewname = "images-list"
    tasks_viewname = "tasks-create"
    task_detail_viewname = "tasks-detail"

    def test_create_image_and_thumbnail(self) -> None:
        session = requests.Session()
        csrf_headers = self._login(session)
        image_id, upload_url = self._create_image(session, csrf_headers)
        self._upload_to_s3(upload_url)
        task_id = self._trigger_task(session, csrf_headers, image_id)

        # infra check
        self._poll_until_done(session, task_id)
        self._assert_thumbnail_exists(upload_url)
        self._assert_jaeger_trace(image_id)

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
        assert resp.status_code == HTTPStatus.CREATED, (
            f"create image failed: {resp.text}"
        )
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
        assert resp.status_code == HTTPStatus.CREATED, (
            f"create task failed: {resp.text}"
        )
        return resp.json()["task_id"]

    def _poll_until_done(self, session: requests.Session, task_id: str) -> None:
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

    def _assert_thumbnail_exists(self, upload_url: str) -> None:
        # original key: users/<id>/<uuid>/<stem>.<ext>
        # thumbnail key: users/<id>/<uuid>/<stem>_thumbnail.<ext>
        object_key = urllib.parse.urlparse(upload_url).path.lstrip("/")
        bucket, _, original_key = object_key.partition("/")
        stem, dot, ext = original_key.rpartition(".")
        thumbnail_key = f"{stem}_thumbnail{dot}{ext}"
        internal_s3._client.head_object(Bucket=bucket, Key=original_key)
        internal_s3._client.head_object(Bucket=bucket, Key=thumbnail_key)

    def _assert_jaeger_trace(self, image_id: str) -> None:
        time.sleep(5)  # BSP flush buffer
        data = _query_jaeger_trace(image_id)
        assert data["data"], f"no Jaeger trace for image_id={image_id}"
        service_names = [
            p["serviceName"] for p in data["data"][0]["processes"].values()
        ]
        assert "django-thumbnail-app" in service_names, (
            f"missing web span. services={service_names}"
        )
        assert "django-thumbnail-worker" in service_names, (
            f"missing worker span. services={service_names}"
        )
