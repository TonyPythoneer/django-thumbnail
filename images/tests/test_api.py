import json
from collections.abc import Iterator
from http import HTTPStatus
from unittest.mock import patch

import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse
from pytest_django.fixtures import DjangoAssertNumQueries

from images.models import Image, ImageStatus, ImageTask

from .factories import USER_PLAIN_PASSWORD, make_image, make_image_task
from .utils import make_image_buf

pytestmark = pytest.mark.django_db


MOCK_PRESIGN = "http://minio/presigned-url"


@pytest.fixture(autouse=True)
def mock_s3() -> Iterator[None]:
    with (
        patch("images.storage.public_s3.presign_put", return_value=MOCK_PRESIGN),
        patch("images.storage.public_s3.presign_get", return_value=MOCK_PRESIGN),
        patch("images.storage.internal_s3.delete"),
        patch("images.storage.internal_s3.upload"),
    ):
        yield


class TestAuth:
    login_viewname = "auth-login"
    logout_viewname = "auth-logout"

    @pytest.mark.parametrize(
        ("password", "expected_status"),
        [
            (USER_PLAIN_PASSWORD, HTTPStatus.OK),
            ("wrong", HTTPStatus.UNAUTHORIZED),
        ],
        ids=["valid", "wrong_password"],
    )
    def test_login(
        self,
        client: Client,
        user: User,
        password: str,
        expected_status: HTTPStatus,
    ) -> None:
        resp = client.post(
            reverse(self.login_viewname),
            data=json.dumps({"username": user.username, "password": password}),
            content_type="application/json",
        )
        assert resp.status_code == expected_status
        if expected_status == HTTPStatus.OK:
            assert resp.json()["user"] == user.username

    def test_logout(self, auth_client: tuple[Client, User]) -> None:
        client, _ = auth_client
        resp = client.post(reverse(self.logout_viewname))
        assert resp.status_code == HTTPStatus.OK


class TestImagesAPI:
    list_viewname = "images-list"
    detail_viewname = "images-detail"

    @pytest.mark.parametrize(
        ("payload", "expected_status"),
        [
            ({"filename": "test.jpg"}, HTTPStatus.CREATED),
            ({}, HTTPStatus.BAD_REQUEST),
        ],
        ids=["valid", "missing_filename"],
    )
    def test_create(
        self,
        auth_client: tuple[Client, User],
        payload: dict[str, str],
        expected_status: HTTPStatus,
    ) -> None:
        client, _ = auth_client
        resp = client.post(
            reverse(self.list_viewname),
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert resp.status_code == expected_status
        if expected_status == HTTPStatus.CREATED:
            data = resp.json()
            assert Image.objects.filter(id=data["image_id"]).exists()
            assert data["upload_url"] == MOCK_PRESIGN

    def test_list_own_images(self, auth_client: tuple[Client, User]) -> None:
        client, user = auth_client
        make_image(user=user)
        make_image(user=user)
        make_image()  # other user
        resp = client.get(reverse(self.list_viewname))
        assert resp.status_code == HTTPStatus.OK
        assert len(resp.json()["images"]) == 2

    def test_list_query_count_constant(
        self,
        auth_client: tuple[Client, User],
        django_assert_num_queries: DjangoAssertNumQueries,
    ) -> None:
        client, user = auth_client
        for _ in range(5):
            img = make_image(user=user)
            make_image_task(image=img)
        # Warm the response once so per-test setup (session/auth) is steady.
        client.get(reverse(self.list_viewname))
        with django_assert_num_queries(4):  # session + user + images + tasks prefetch
            client.get(reverse(self.list_viewname))

    @pytest.mark.parametrize(
        ("owned", "expected_status", "image_remains"),
        [
            (True, HTTPStatus.OK, False),
            (False, HTTPStatus.NOT_FOUND, True),
        ],
        ids=["owner", "other_user"],
    )
    def test_delete(
        self,
        auth_client: tuple[Client, User],
        other_user: User,
        owned: bool,
        expected_status: HTTPStatus,
        image_remains: bool,
    ) -> None:
        client, user = auth_client
        owner = user if owned else other_user
        image = make_image(user=owner)
        resp = client.delete(reverse(self.detail_viewname, kwargs={"image_id": image.id}))
        assert resp.status_code == expected_status
        assert Image.objects.filter(id=image.id).exists() == image_remains

    def test_unauthenticated(self, client: Client) -> None:
        resp = client.get(reverse(self.list_viewname))
        assert resp.status_code == HTTPStatus.UNAUTHORIZED


class TestTasksAPI:
    list_viewname = "tasks-create"
    detail_viewname = "tasks-detail"

    @pytest.mark.parametrize(
        ("payload_kind", "expected_status", "task_created"),
        [
            ("own", HTTPStatus.CREATED, True),
            ("missing", HTTPStatus.BAD_REQUEST, False),
            ("other_user", HTTPStatus.NOT_FOUND, False),
        ],
        ids=["own", "missing_image_id", "other_user"],
    )
    def test_create_task(
        self,
        auth_client: tuple[Client, User],
        other_user: User,
        payload_kind: str,
        expected_status: HTTPStatus,
        task_created: bool,
    ) -> None:
        client, user = auth_client
        if payload_kind == "own":
            image = make_image(user=user)
            payload: dict[str, str] = {"image_id": str(image.id)}
        elif payload_kind == "other_user":
            image = make_image(user=other_user)
            payload = {"image_id": str(image.id)}
        else:
            payload = {}
        with (
            patch("images.tasks.internal_s3.download") as mock_dl,
            patch("images.tasks.internal_s3.upload"),
        ):
            mock_dl.return_value = make_image_buf()
            resp = client.post(
                reverse(self.list_viewname),
                data=json.dumps(payload),
                content_type="application/json",
            )
        assert resp.status_code == expected_status
        if task_created:
            data = resp.json()
            assert ImageTask.objects.filter(id=data["task_id"]).exists()

    @pytest.mark.parametrize(
        ("owned", "expected_status"),
        [
            (True, HTTPStatus.OK),
            (False, HTTPStatus.NOT_FOUND),
        ],
        ids=["owner", "other_user"],
    )
    def test_get_task(
        self,
        auth_client: tuple[Client, User],
        other_user: User,
        owned: bool,
        expected_status: HTTPStatus,
    ) -> None:
        client, user = auth_client
        owner = user if owned else other_user
        image = make_image(user=owner)
        task = make_image_task(image=image, status=ImageStatus.DONE)
        resp = client.get(reverse(self.detail_viewname, kwargs={"task_id": task.id}))
        assert resp.status_code == expected_status
        if expected_status == HTTPStatus.OK:
            assert resp.json()["status"] == ImageStatus.DONE

    def test_cancel_task(self, auth_client: tuple[Client, User]) -> None:
        client, user = auth_client
        image = make_image(user=user)
        task = make_image_task(image=image, status=ImageStatus.PENDING)
        with patch("images.views.AsyncResult"):
            resp = client.delete(reverse(self.detail_viewname, kwargs={"task_id": task.id}))
        assert resp.status_code == HTTPStatus.OK
        task.refresh_from_db()
        assert task.status == ImageStatus.FAILED

    def test_unauthenticated(self, client: Client) -> None:
        resp = client.post(
            reverse(self.list_viewname),
            data=json.dumps({}),
            content_type="application/json",
        )
        assert resp.status_code == HTTPStatus.UNAUTHORIZED
