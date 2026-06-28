"""Celery application for background imports and recalculations."""

import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("hr_vidnova")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# Періодичний синк PeopleForce (час — у CELERY_TIMEZONE).
app.conf.beat_schedule = {
    "peopleforce-light-nightly": {
        "task": "integrations.sync_peopleforce_light",
        "schedule": crontab(minute=0, hour=3, day_of_week="mon,tue,wed,thu,fri,sat"),
    },
    "peopleforce-full-weekly": {
        "task": "integrations.sync_peopleforce_full",
        "schedule": crontab(minute=0, hour=3, day_of_week="sun"),
    },
}
