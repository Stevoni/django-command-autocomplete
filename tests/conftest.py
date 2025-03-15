import os
import django
from django.conf import settings


def pytest_configure():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")

    settings.configure(
        DEBUG=True,
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": ":memory:",
            }
        },
        INSTALLED_APPS=[
            "django_command_autocomplete",
        ],
        SECRET_KEY="test-key",
    )

    django.setup()
