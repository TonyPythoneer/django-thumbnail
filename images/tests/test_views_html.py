from http import HTTPStatus
from unittest.mock import patch

import pytest
from django.urls import reverse

from images.models import Image, ImageTask

from .factories import ImageFactory, ImageTaskFactory

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


class TestGallery:
    def test_gallery_requires_login(self, client):
        resp = client.get(reverse("gallery"))
        assert resp.status_code == HTTPStatus.FOUND
        assert "/login/" in resp["Location"]

    def test_gallery_shows_own_images_only(self, auth_client):
        client, user = auth_client
        ImageFactory(user=user)
        ImageFactory(user=user)
        ImageFactory()  # other user
        resp = client.get(reverse("gallery"))
        assert resp.status_code == HTTPStatus.OK
        assert len(resp.context["images"]) == 2

    def test_gallery_query_count_constant(self, auth_client, django_assert_num_queries):
        client, user = auth_client
        for _ in range(5):
            img = ImageFactory(user=user)
            ImageTaskFactory(image=img)
        with django_assert_num_queries(4):  # session auth + user + images + tasks prefetch
            client.get(reverse("gallery"))


class TestUpload:
    def test_upload_get_renders_form(self, auth_client):
        client, _ = auth_client
        resp = client.get(reverse("upload"))
        assert resp.status_code == HTTPStatus.OK

    def test_upload_post_creates_image_and_dispatches_task(self, auth_client):
        client, user = auth_client
        from django.core.files.uploadedfile import SimpleUploadedFile
        from .utils import make_image_buf

        buf = make_image_buf()
        f = SimpleUploadedFile("test.jpg", buf.getvalue(), content_type="image/jpeg")
        with (
            patch("images.tasks.internal_s3.download", return_value=make_image_buf()),
            patch("images.tasks.internal_s3.upload"),
        ):
            resp = client.post(reverse("upload"), {"file": f})
        assert resp.status_code == HTTPStatus.FOUND
        assert Image.objects.filter(user=user).exists()


class TestHtmlLogin:
    def test_redirects_authenticated_user(self, auth_client):
        client, _ = auth_client
        resp = client.get(reverse("login"))
        assert resp.status_code == HTTPStatus.FOUND
        assert resp["Location"].endswith(reverse("gallery"))


class TestImageDelete:
    def test_delete_own_image(self, auth_client):
        client, user = auth_client
        image = ImageFactory(user=user)
        resp = client.post(reverse("image-delete", kwargs={"image_id": image.id}))
        assert resp.status_code == HTTPStatus.FOUND
        assert not Image.objects.filter(id=image.id).exists()

    def test_cannot_delete_other_user_image(self, auth_client, other_user):
        client, _ = auth_client
        image = ImageFactory(user=other_user)
        resp = client.post(reverse("image-delete", kwargs={"image_id": image.id}))
        assert resp.status_code == HTTPStatus.FOUND  # redirects to gallery
        assert Image.objects.filter(id=image.id).exists()  # not deleted
