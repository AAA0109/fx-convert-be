import os

from django.db   import connection

from main.apps.oems.backend.db import DbAdaptor

"""
# from django.conf import settings
# from django.apps import apps

# https://stackoverflow.com/questions/34300513/using-django-model-outside-of-the-django-framework
conf = {
    'INSTALLED_APPS': [
        'Demo'
    ],
    'DATABASES': {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.path.join('.', 'db.sqlite3'),
        }
    }
}

settings.configure(**conf)
apps.populate(settings.INSTALLED_APPS)
"""

def init_db():
    if not hasattr(init_db, '_db'):
        # dbconn = connection._connections['default'].client.connection
        init_db._db = DbAdaptor(connection=connection, autoconnect=False)
    return init_db._db

# =============================

def ensure_queue_table( topics=[], table_name='global1' ):
    db = init_db() # nop
    sql = db.ensure_queue( topics, queue_table=table_name, return_cmd=True )
    with connection.cursor() as cursor:
        cursor.execute(sql)

# =============================

def enqueue(topic, data, uid=None, action=None, source=None, **kwargs):
    db = init_db() # nop
    sql = db.enqueue( topic, data, uid=uid, action=action, source=source, returning='eid', return_cmd=True, **kwargs)
    with connection.cursor() as cursor:
        cursor.execute(sql)
        row = cursor.fetchone()
    try:
        return row[0]
    except:
        return row

# =============================

def del_queue(qid, **kwargs):
    db = init_db()
    sql = db.del_queue( qid, return_cmd=True, **kwargs)
    with connection.cursor() as cursor:
        cursor.execute(sql)

# =============================

def get_queue_response(qid, **kwargs ):
    db = init_db()
    sql = db.get_queue_response( qid, return_cmd=True, **kwargs)
    with connection.cursor() as cursor:
        cursor.execute(sql)
        
# =============================

