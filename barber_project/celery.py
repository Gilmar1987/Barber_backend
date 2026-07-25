# barber_project/celery.py
import os
from celery import Celery

# Define o módulo de configurações do Django para o Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'barber_project.settings')

app = Celery('barber_project')

# Carrega as configurações do Django (ex: CELERY_BROKER_URL do settings.py)
app.config_from_object('django.conf:settings', namespace='CELERY')

# Descobre automaticamente as tasks em todos os apps registrados
app.autodiscover_tasks([
    'apps.core',
    'apps.tenants',
    'apps.operacional',
    'apps.agenda',  # ✅ Essencial para a US04
])

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')