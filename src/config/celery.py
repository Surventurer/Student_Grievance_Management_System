import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('student_grievance_system')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')

# Configure periodic tasks
app.conf.beat_schedule = {
    'check-sla-escalations-every-hour': {
        'task': 'apps.grievances.tasks.check_sla_and_escalate',
        'schedule': 3600.0,  # Run every hour (3600 seconds)
    },
}
