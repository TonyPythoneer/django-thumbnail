import uuid

import factory
from django.contrib.auth.models import User

from images.models import Image, ImageStatus, ImageTask


USER_PLAIN_PASSWORD = "password"


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Faker("email")
    email = factory.LazyAttribute(lambda o: o.username)
    password = factory.PostGenerationMethodCall("set_password", USER_PLAIN_PASSWORD)


class ImageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Image

    user = factory.SubFactory(UserFactory)
    original_filename = factory.Faker("file_name", extension="jpg")
    original_key = factory.LazyAttribute(lambda o: Image.format_key(o.user.id, uuid.uuid4(), o.original_filename))
    thumbnail_key = factory.LazyAttribute(lambda o: Image.format_thumbnail_key_from_original(o.original_key))


class ImageTaskFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ImageTask

    image = factory.SubFactory(ImageFactory)
    status = ImageStatus.PENDING
