
from __future__ import absolute_import, unicode_literals

import os
from django.conf import settings
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rsvp.settings')

app = Celery('rsvp')

app.conf.broker_url = settings.CELERY_BROKER_URL

app.config_from_object('django.conf:settings', namespace='CELERY')


app.autodiscover_tasks(['communication.tasks'])
