from __future__ import absolute_import, unicode_literals

import os

from celery import Celery, shared_task
from celery.signals import setup_logging

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'main.settings.local')

app = Celery('main')

app.config_from_object('django.conf:settings', namespace='CELERY')

modules_to_discover = [
    'main.apps.billing',
    'main.apps.cashflow',
    'main.apps.core',
    'main.apps.corpay',
    'main.apps.dataprovider',
    'main.apps.hedge',
    'main.apps.margin',
    'main.apps.marketdata',
    'main.apps.oems',
    'main.apps.payment',
    'main.apps.reports',
    'main.apps.webhook'
]




app.autodiscover_tasks(packages=modules_to_discover)


@setup_logging.connect
def config_loggers(*args, **kwags):
    from logging.config import dictConfig
    from django.conf import settings
    dictConfig(settings.LOGGING)


@shared_task(time_limit=60)
def celery_heartbeat(msg: str = "NO MESSAGE"):
    import logging
    logger = logging.getLogger("root")
    logger.debug(f'celery_heartbeat: {msg}')
    return msg


@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    try:
        # Calls test('celery heartbeat') every 60 seconds.
        sender.add_periodic_task(60.0, celery_heartbeat.s('celery heartbeat'), name='celery heartbeat every minute')
    except Exception as e:
        pass
