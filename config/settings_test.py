"""Ajustes para correr las pruebas sin MySQL: python manage.py test --settings=config.settings_test"""
from .settings import *  # noqa

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]  # pruebas más rápidas
MEDIA_ROOT = BASE_DIR / "media_test"
