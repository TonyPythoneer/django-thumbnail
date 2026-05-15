import pytest
from pytest_django.fixtures import DjangoAssertNumQueries

from images.models import Image, ImageStatus

from .factories import make_image, make_image_task

pytestmark = pytest.mark.django_db


class TestLatestTask:
    def test_latest_task_returns_newest(self) -> None:
        image = make_image()
        older = make_image_task(image=image, status=ImageStatus.FAILED)
        assert image.latest_task().id == older.id

        newer = make_image_task(image=image, status=ImageStatus.DONE)
        assert image.latest_task().id == newer.id

    def test_latest_task_none_when_no_tasks(self) -> None:
        image = make_image()
        assert image.latest_task() is None

    def test_current_status_reflects_newest_task(self) -> None:
        image = make_image()
        make_image_task(image=image, status=ImageStatus.FAILED)
        make_image_task(image=image, status=ImageStatus.DONE)
        assert image.current_status() == ImageStatus.DONE

    def test_current_status_pending_when_no_tasks(self) -> None:
        image = make_image()
        assert image.current_status() == ImageStatus.PENDING

    def test_latest_task_uses_prefetch_cache(
        self, django_assert_num_queries: DjangoAssertNumQueries
    ) -> None:
        image = make_image()
        make_image_task(image=image, status=ImageStatus.FAILED)
        make_image_task(image=image, status=ImageStatus.DONE)

        with django_assert_num_queries(2):  # 1 images + 1 prefetch tasks
            qs = Image.objects.filter(id=image.id).prefetch_related("tasks")
            for img in qs:
                img.latest_task()
