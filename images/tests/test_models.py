import pytest

from images.models import Image, ImageStatus

from .factories import ImageFactory, ImageTaskFactory

pytestmark = pytest.mark.django_db


class TestLatestTask:
    def test_latest_task_returns_newest(self):
        image = ImageFactory()
        older = ImageTaskFactory(image=image, status=ImageStatus.FAILED)
        assert image.latest_task().id == older.id

        newer = ImageTaskFactory(image=image, status=ImageStatus.DONE)
        assert image.latest_task().id == newer.id

    def test_latest_task_none_when_no_tasks(self):
        image = ImageFactory()
        assert image.latest_task() is None

    def test_current_status_reflects_newest_task(self):
        image = ImageFactory()
        ImageTaskFactory(image=image, status=ImageStatus.FAILED)
        ImageTaskFactory(image=image, status=ImageStatus.DONE)
        assert image.current_status() == ImageStatus.DONE

    def test_current_status_pending_when_no_tasks(self):
        image = ImageFactory()
        assert image.current_status() == ImageStatus.PENDING

    def test_latest_task_uses_prefetch_cache(self, django_assert_num_queries):
        image = ImageFactory()
        ImageTaskFactory(image=image, status=ImageStatus.FAILED)
        ImageTaskFactory(image=image, status=ImageStatus.DONE)

        with django_assert_num_queries(2):  # 1 images + 1 prefetch tasks
            qs = Image.objects.filter(id=image.id).prefetch_related("tasks")
            for img in qs:
                img.latest_task()
