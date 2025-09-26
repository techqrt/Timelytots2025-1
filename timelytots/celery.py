from celery import Celery
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'timelytots.settings')

app = Celery('timelytots')
app.config_from_object('django.conf:settings', namespace='CELERY')

# This will auto-discover tasks in all installed apps
app.autodiscover_tasks()
