import os

from celery import Celery


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "web_natrent.settings")
app = Celery("web_natrent")
app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()
