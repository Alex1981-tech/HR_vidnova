"""Celery application for background imports and recalculations."""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("hr_vidnova")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
