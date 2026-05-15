import json
from http import HTTPStatus
from unittest.mock import patch

import pytest
from django.urls import reverse

from images.models import Image, ImageStatus, ImageTask

from .factories import USER_PLAIN_PASSWORD, ImageFactory, ImageTaskFactory
from .utils import make_image_buf

pytestmark = pytest.mark.django_db


MOCK_PRESIGN = "http://minio/presigned-url"


@pytest.fixture(autouse=True)
def mock_s3():
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

    def test_login_success(self, client, user):
        resp = client.post(
            reverse(self.login_viewname),
            data=json.dumps({"username": user.username, "password": USER_PLAIN_PASSWORD}),
            content_type="application/json",
        )
        assert resp.status_code == HTTPStatus.OK
        assert resp.json()["user"] == user.username

    def test_login_invalid_credentials(self, client, user):
        resp = client.post(
            reverse(self.login_viewname),
            data=json.dumps({"username": user.username, "password": "wrong"}),
            content_type="application/json",
        )
        assert resp.status_code == HTTPStatus.UNAUTHORIZED

    def test_logout(self, auth_client):
        client, _ = auth_client
        resp = client.post(reverse(self.logout_viewname))
        assert resp.status_code == HTTPStatus.OK


class TestImagesAPI:
    list_viewname = "images-list"
    detail_viewname = "images-detail"

    def test_create_returns_presigned_url(self, auth_client):
        client, _ = auth_client
        resp = client.post(
            reverse(self.list_viewname),
            data=json.dumps({"filename": "test.jpg"}),
            content_type="application/json",
        )
        assert resp.status_code == HTTPStatus.CREATED
        data = resp.json()
        assert Image.objects.filter(id=data["image_id"]).exists()
        assert data["upload_url"] == MOCK_PRESIGN

    def test_create_missing_filename(self, auth_client):
        client, _ = auth_client
        resp = client.post(
            reverse(self.list_viewname),
            data=json.dumps({}),
            content_type="application/json",
        )
        assert resp.status_code == HTTPStatus.BAD_REQUEST

    def test_list_own_images(self, auth_client):
        client, user = auth_client
        ImageFactory(user=user)
        ImageFactory(user=user)
        ImageFactory()  # other user
        resp = client.get(reverse(self.list_viewname))
        assert resp.status_code == HTTPStatus.OK
        assert len(resp.json()["images"]) == 2

    def test_delete_image(self, auth_client):
        client, user = auth_client
        image = ImageFactory(user=user)
        resp = client.delete(reverse(self.detail_viewname, kwargs={"image_id": image.id}))
        assert resp.status_code == HTTPStatus.OK
        assert not Image.objects.filter(id=image.id).exists()

    def test_delete_other_user_image(self, auth_client, other_user):
        client, _ = auth_client
        image = ImageFactory(user=other_user)
        resp = client.delete(reverse(self.detail_viewname, kwargs={"image_id": image.id}))
        assert resp.status_code == HTTPStatus.NOT_FOUND
        assert Image.objects.filter(id=image.id).exists()

    def test_unauthenticated(self, client):
        resp = client.get(reverse(self.list_viewname))
        assert resp.status_code == HTTPStatus.UNAUTHORIZED


class TestTasksAPI:
    list_viewname = "tasks-create"
    detail_viewname = "tasks-detail"

    def test_create_task(self, auth_client):
        client, user = auth_client
        image = ImageFactory(user=user)
        with (
            patch("images.tasks.internal_s3.download") as mock_dl,
            patch("images.tasks.internal_s3.upload"),
        ):
            mock_dl.return_value = make_image_buf()
            resp = client.post(
                reverse(self.list_viewname),
                data=json.dumps({"image_id": str(image.id)}),
                content_type="application/json",
            )
        assert resp.status_code == HTTPStatus.CREATED
        data = resp.json()
        assert ImageTask.objects.filter(id=data["task_id"]).exists()

    def test_create_task_missing_image_id(self, auth_client):
        client, _ = auth_client
        resp = client.post(
            reverse(self.list_viewname),
            data=json.dumps({}),
            content_type="application/json",
        )
        assert resp.status_code == HTTPStatus.BAD_REQUEST

    def test_create_task_other_user_image(self, auth_client, other_user):
        client, _ = auth_client
        image = ImageFactory(user=other_user)
        resp = client.post(
            reverse(self.list_viewname),
            data=json.dumps({"image_id": str(image.id)}),
            content_type="application/json",
        )
        assert resp.status_code == HTTPStatus.NOT_FOUND

    def test_get_task_status(self, auth_client):
        client, user = auth_client
        image = ImageFactory(user=user)
        task = ImageTaskFactory(image=image, status=ImageStatus.DONE)
        resp = client.get(reverse(self.detail_viewname, kwargs={"task_id": task.id}))
        assert resp.status_code == HTTPStatus.OK
        assert resp.json()["status"] == ImageStatus.DONE

    def test_get_task_other_user(self, auth_client, other_user):
        client, _ = auth_client
        image = ImageFactory(user=other_user)
        task = ImageTaskFactory(image=image)
        resp = client.get(reverse(self.detail_viewname, kwargs={"task_id": task.id}))
        assert resp.status_code == HTTPStatus.NOT_FOUND

    def test_cancel_task(self, auth_client):
        client, user = auth_client
        image = ImageFactory(user=user)
        task = ImageTaskFactory(image=image, status=ImageStatus.PENDING)
        with patch("images.views.AsyncResult"):
            resp = client.delete(reverse(self.detail_viewname, kwargs={"task_id": task.id}))
        assert resp.status_code == HTTPStatus.OK
        task.refresh_from_db()
        assert task.status == ImageStatus.FAILED

    def test_unauthenticated(self, client):
        resp = client.post(
            reverse(self.list_viewname),
            data=json.dumps({}),
            content_type="application/json",
        )
        assert resp.status_code == HTTPStatus.UNAUTHORIZED
