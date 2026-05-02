
from __future__ import absolute_import, unicode_literals

import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rsvp.settings')

app = Celery('rsvp')

app.config_from_object('django.conf:settings', namespace='CELERY')

# Configure broker connection with retry settings
app.conf.broker_connection_retry_on_startup = True
app.conf.broker_connection_retry = True
app.conf.broker_connection_max_retries = 10

# Auto-discover tasks from all installed apps
app.autodiscover_tasks()

# Celery Beat Schedule - Periodic tasks
app.conf.beat_schedule = {
    'mark-finished-events': {
        'task': 'events.tasks.mark_finished_events',
        'schedule': 3600.0,  # Every hour
    },
    'send-event-reminders': {
        'task': 'events.tasks.send_event_reminders',
        'schedule': crontab(hour=9, minute=0),  # Daily at 9 AM
    },
    'daily-analytics-summary': {
        'task': 'analytics.tasks.daily_analytics_summary',
        'schedule': crontab(hour=0, minute=0),  # Daily at midnight
    },
    'refresh-all-analytics': {
        'task': 'analytics.tasks.refresh_all_analytics',
        'schedule': crontab(hour=1, minute=0),  # Daily at 1 AM
    },
}

# Task routing for different queues
app.conf.task_default_queue = 'default'
app.conf.task_default_exchange = 'default'
app.conf.task_default_routing_key = 'default'
