import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "django_thumbnail.settings.local")

application = get_wsgi_application()
