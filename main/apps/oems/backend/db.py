import hashlib
import socket
import sqlite3
import time
import uuid
from datetime import datetime
from math import isnan
from uuid import uuid4, UUID

import psycopg2
from psycopg2 import InterfaceError, OperationalError
from psycopg2.extras import RealDictCursor

try:
    from psycopg2.errors import AdminShutdown
except ImportError:
    print("Failed to import AdminShutdown.")
    AdminShutdown = OperationalError

# ======================================

try:
    from django.conf import settings
except ImportError:
    settings = None

# ======================================

from main.apps.oems.backend.utils import jsonify

# build a db connection class that handles connects, cursor, and reconnects.
# add function to ensure tables, schemas, indexes

PG_DISCONNECTS = (InterfaceError, AdminShutdown, OperationalError)
SQLITE_DISCONNECTS = tuple()


# ==============================

def get_lock_index(lock_name, base=32):
    return int(hashlib.sha256(lock_name.encode('utf-8')).hexdigest(), 16) % 2 ** base


# ==============================

def ensure_handle(fn):
    def wrapper(self, *args, **kwargs):
        if not self.connection or (self.dbtype == 'POSTGRES' and self.connection.closed):  # or if connection closed
            self.connection = self.connect(self)
        if not self.cursor or (self.dbtype == 'POSTGRES' and self.cursor.closed):
            self.cursor = self.connection.cursor()  # this is the default cursor
        ret = fn(self, *args, **kwargs)
        return ret

    return wrapper


def open_transaction(fn):
    def wrapper(self, *args, **kwargs):
        try:
            ret = fn(self, *args, **kwargs)
        except self.DISCONNECTS as e:
            check = self.check_db_connection('open')
            if check and self.retry_safe:
                ret = fn(self, *args, **kwargs)
            else:
                raise e
        except:
            raise
        self.in_tran = True
        return ret

    return wrapper


def close_transaction(fn):
    def wrapper(self, *args, **kwargs):
        try:
            ret = fn(self, *args, **kwargs)
        except self.DISCONNECTS as e:
            # self.check_db_connection( 'close' ) # cannot reconnect to database in the middle of a transaction
            raise e
        # close the cursor
        if self.cursor:
            self.cursor.close()
            self.cursor = None
        self.in_tran = False
        return ret

    return wrapper


def rollback_transaction(fn):
    def wrapper(self, *args, **kwargs):
        try:
            ret = fn(self, *args, **kwargs)
        except self.DISCONNECTS as e:
            # self.check_db_connection( 'close' ) # cannot reconnect to database in the middle of a transaction
            raise e
        except:
            self.rollback()
            raise
        return ret

    return wrapper


# ===============================

def postgres_escape(value):
    if value is None:
        return 'NULL'
    elif isinstance(value, bool):
        return 'TRUE' if value else 'FALSE'
    elif isinstance(value, (int, float)):
        return str(value)
    elif isinstance(value, datetime):
        return f"'{value.isoformat()}'"
    elif isinstance(value, str):
        # Escape single quotes by doubling them
        escaped_value = value.replace("'", "''")
        # Wrap the string in single quotes
        return f"'{escaped_value}'"
    elif isinstance(value, uuid.UUID):
        # Handle UUID objects
        return f"'{str(value)}'"
    elif isinstance(value, dict):
        # Convert dictionary to JSON string and escape it
        json_string = jsonify(value)
        escaped_json = json_string.replace("'", "''")
        return f"'{escaped_json}'"
    else:
        raise ValueError(f"Unsupported type for SQL conversion: {type(value)}")


def postgres_type(x):
    if x is None:
        return 'NULL'
    elif isinstance(x, bool):
        return str(x).lower()  # could be "true" or "false"
    elif isinstance(x, str):
        return f"'{x}'"
    elif isinstance(x, int):
        return str(x)
    elif isinstance(x, float):
        return str(x) if not isnan(x) else 'NULL'
    elif isinstance(x, datetime):
        return f"'{x.isoformat()}'"
    elif isinstance(x, UUID):
        return f"'{x}'"
    else:
        return f"'{jsonify(x)}'::jsonb"


def connect_postgres(self):
    try:
        # print( 'connecting postgres', self.host, self.port, self.username, self.password, self.database )
        connection = psycopg2.connect(host=self.host, port=self.port, user=self.username,
                                      password=self.password, database=self.database,
                                      application_name=self.application_name,
                                      cursor_factory=RealDictCursor)
        connection.set_session(readonly=self.readonly, autocommit=self.autocommit)
        return connection
    except Exception as e:
        import traceback, sys
        print("ERROR: failed to establish SQL Connection")
        traceback.print_exc(file=sys.stdout)
        return None


def pg_alive(self):
    try:
        sock = socket.fromfd(self.connection.fileno(), socket.AF_INET, socket.SOCK_STREAM)
        return True
    except:
        return False


# ==========================

def connect_sqlite(self):
    conn = sqlite3.connect(self.database, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def sqlite_alive(self):
    return True


def sqlite_type(x):
    if x is None:
        return 'NULL'
    elif isinstance(x, bool):
        return str(x).upper()  # could be "true" or "false"
    elif isinstance(x, str):
        return f"'{x}'"
    elif isinstance(x, int):
        return str(x)
    elif isinstance(x, float):
        return str(x) if not isnan(x) else 'NULL'
    elif isinstance(x, datetime):
        return f"'{x.isoformat()}'"
    else:
        raise ValueError


# =============================================================================

class DbAdaptor:

    def __init__(self, host=None, port=None, database=None,
                 username=None, password=None,
                 application_name=None, dbtype='POSTGRES', connection=None,
                 autocommit=False, readonly=False, autoconnect=True,
                 reconnect=True, quote_safe=False,
                 retry_safe=True, fetchsize=100):

        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.fetchsize = fetchsize
        self.dbtype = dbtype
        self.application_name = application_name
        self.database = database
        self.reconnect = reconnect
        self.retry_safe = retry_safe
        self.autocommit = autocommit
        self.readonly = readonly

        if not application_name:
            self.application_name = 'UNKNOWN'

        self.connection = connection
        self.cursor = None
        self.in_tran = False

        if dbtype == 'POSTGRES':

            self.escape = postgres_escape
            self.pytype = postgres_type
            self.connect = connect_postgres
            self.is_alive = pg_alive
            self.DISCONNECTS = PG_DISCONNECTS
            self.locks = {}

        elif dbtype == 'SQLITE':

            self.escape = postgres_escape
            self.pytype = sqlite_type
            self.connect = connect_sqlite
            self.is_alive = sqlite_alive
            self.DISCONNECTS = PG_DISCONNECTS

        if autoconnect and self.connection is None:
            self.connection = self.connect(self)

    # ===============================

    def check_db_connection(self, typ, max_retries=30):
        # typ can be opening or closing a transaction (open/close as string)
        check = False
        if self.reconnect:
            i = 1
            print('trying to reconnect', i)
            self.connection = self.connect(self)
            check = True
            while not self.is_alive(self):
                print('trying to reconnect', i)
                check = False
                time.sleep(min(64.0, 2 ** i))  # exponential backoff
                i += 1
                self.connection = self.connect(self)
                if i > max_retries:
                    break
                check = True
        return check

    # ==============================

    def subscribe(self, subscription, force=False):
        if subscription not in self.subs or force:
            self.execute_and_commit(f'LISTEN {subscription};')
            self.subs.add(subscription)
            return True
        return False

    # ==============================

    def close(self):
        if self.cursor:
            if self.cursor: self.cursor.close()
            self.cursor = None
            self.in_tran = False
        if self.connection:
            self.connection.close()
            self.connection = None

    # ======================

    def insert_sql(self, schema, table, params, returning=None):
        columns = ','.join(f'"{k}"' for k in params.keys())
        values = ','.join(self.escape(v) for v in params.values())
        full_table = f'"{schema}"."{table}"' if schema and self.dbtype == 'POSTGRES' else f'"{table}"'
        sql = f'INSERT INTO {full_table} ({columns}) VALUES ({values})'

        if returning:
            if isinstance(returning, list):
                rflds = ','.join(f'"{fld}"' for fld in returning)
                sql += f' RETURNING {rflds}'
            else:
                sql += f' RETURNING "{returning}"'

        return sql

    def update_sql(self, schema, table, params, key_fld, key):
        set_clause = ','.join(f'"{k}"={self.escape(v)}' for k, v in params.items() if k != key_fld)
        full_table = f'"{schema}"."{table}"' if schema and self.dbtype == 'POSTGRES' else f'"{table}"'
        return f'UPDATE {full_table} SET {set_clause} WHERE "{key_fld}" = {self.escape(key)}'

    def delete_sql(self, schema, table, key_fld, key):
        full_table = f'"{schema}"."{table}"' if schema and self.dbtype == 'POSTGRES' else f'"{table}"'
        return f'delete from {full_table} where "{key_fld}" = {self.pytype(key)}'

    def select_where(self, schema, table, columns=None, key=None, value=None):
        columns = '*' if columns is None else ','.join(map(self.escape, columns))
        full_table = f'"{schema}"."{table}"' if schema and self.dbtype == 'POSTGRES' else f'"{table}"'
        if key:
            return f'select {columns} from {full_table} where "{key}" = {self.pytype(value)}'
        else:
            return f'select {columns} from {full_table}'

    # ======================

    @open_transaction
    @ensure_handle
    def execute(self, *args, **kwargs):
        return self.cursor.execute(*args, **kwargs)

    @open_transaction
    @ensure_handle
    def executemany(self, *args, **kwargs):
        return self.cursor.executemany(*args, **kwargs)

    @open_transaction
    @ensure_handle
    def fetchone(self, *args, **kwargs):
        return self.cursor.fetchone(*args, **kwargs)

    @open_transaction
    @ensure_handle
    def fetchmany(self, *args, **kwargs):
        return self.cursor.fetchmany(*args, **kwargs)

    @open_transaction
    @ensure_handle
    def fetchall(self, *args, **kwargs):
        return self.cursor.fetchall(*args, **kwargs)

    @close_transaction
    def commit(self, *args, **kwargs):
        return self.connection.commit(*args, **kwargs)

    @close_transaction
    def rollback(self, *args, **kwargs):
        return self.connection.rollback(*args, **kwargs)

    @ensure_handle
    def mogrify(self, *args, **kwargs):
        return self.cursor.mogrify(*args, **kwargs)

    # =========================================================================

    @rollback_transaction
    def fetch_and_commit(self, *args, one_call=True, fetchsize=None, dry_run=False, **kwargs):

        if dry_run:
            print(args[0])
            return []

        if fetchsize is None: fetchsize = self.fetchsize

        self.execute(*args, **kwargs)
        if one_call:
            ret = self.fetchall()
        else:
            ret = [dict(row) for row in self.fetchmany(size=fetchsize)]
            while ret:
                rows = self.fetchmany(size=fetchsize)
                if rows:
                    ret += [dict(row) for row in rows]
                else:
                    break
        self.commit()
        return ret

    @rollback_transaction
    def fetch_and_commit_yield(self, *args, one_call=False, fetchsize=None, **kwargs):
        if fetchsize is None: fetchsize = self.fetchsize
        self.execute(*args, **kwargs)
        ret = True
        if one_call:
            rows = self.fetchall()
            self.commit()
            yield rows
        else:
            while ret:
                rows = self.fetchmany(size=fetchsize)
                if rows:
                    yield rows
                else:
                    break
            self.commit()
        return ret

    # ======================================================================

    @rollback_transaction
    def execute_and_commit(self, *args, **kwargs):
        self.execute(*args, **kwargs)
        self.commit()

    # =========================================================================

    def ensure_db_objects(self, config, sync_schema=True, drop=False, truncate=False, dry_run=False):
        """
        Since DB objects are not exposed to the outside world, we do not worry
        about SQL injection.
        """

        cmds = []
        schema = config['schema']
        table_name = config['table_name']

        if self.dbtype == 'POSTGRES':
            schema = config['schema']
            table_name = config['table_name']
            full_table = f'"{schema}"."{table_name}"'
        else:
            schema = None
            table_name = config['table_name']
            full_table = f'"{table_name}"'

        if drop:
            cmds.append(f'drop table if exists {full_table} cascade;')
        elif truncate:
            cmds.append(f'truncate table {full_table};')

        if schema and schema != 'public':
            cmds.append(f'create schema if not exists "{schema}";')

        columns = [f'"{k}" {v}' for k, v in config['columns'].items()]
        if 'primary_key' in config:
            columns.append(f'PRIMARY KEY ("{config["primary_key"]}")')
        cmds.append(f'create table if not exists {full_table} ({",".join(columns)});')

        if 'indexes' in config:
            for name, index in config['indexes'].items():
                index_name = '_'.join((table_name, name))
                index_columns = [f'"{col}"' for col in index]
                cmds.append(f'create index if not exists "{index_name}" on {full_table} ({",".join(index_columns)});')

        if sync_schema:
            _cmds = []
            for column, column_type in config['columns'].items():
                _cmds.append(f'add column if not exists "{column}" {column_type}')
            cmds.append(f'alter table "{schema}"."{table_name}" %s;' % (','.join(_cmds)))

        cmd = ' '.join(cmds)

        if not dry_run:
            self.execute_and_commit(cmd)
        else:
            print(cmd)

    # =========================================================================
    # these are session level locks that are given up at upon release of connection failure
    # only works with postgres

    def acquire_lock(self, lock_name, ind=None, nowait=False, commit=True):

        if lock_name in self.locks:
            print("ERROR: cannot acquire same lock twice")
            return False
        else:

            if ind is None:
                ind = get_lock_index(lock_name)

            # this is a blocking exclusive lock
            try:
                if nowait:
                    cmd = 'SELECT pg_try_advisory_lock(%d);' % ind
                    self.execute(cmd)
                    ret = self.fetchall()
                    if commit:
                        self.commit()
                    ret = ret[0]['pg_try_advisory_lock']
                    if ret:
                        self.locks[lock_name] = ind
                    return ret
                else:
                    cmd = 'SELECT pg_advisory_lock(%d);' % ind
                    self.execute(cmd)
                    if commit:
                        self.commit()
                    self.locks[lock_name] = ind
                    return True
            except Exception as e:
                print(e)
                if commit:
                    self.rollback()
                return False

    def release_lock(self, lock_name, commit=True):

        if lock_name not in self.locks:
            print("ERROR: lock not acquired, cannot release")
            return False
        else:
            ind = self.locks[lock_name]
            try:
                cmd = 'SELECT pg_advisory_unlock(%d);' % ind
                self.execute(cmd)
                ret = self.fetchall()
                if commit:
                    self.commit()
                del self.locks[lock_name]
                return ret[0]['pg_advisory_unlock']
            except Exception as e:
                print(e)
                if commit:
                    self.rollback()
                return False

    def release_sorted_locks(self, locks, commit=True):

        ret = dict.fromkeys(locks)

        if locks and self.locks:
            keys = list(self.locks, keys())
            for lock in reversed(keys):
                if lock in locks:
                    val = self.release_lock(lock, commit=commit)
                    ret[lock] = val

        return ret

    def clear_locks(self, commit=True):

        try:
            self.execute('select pg_advisory_unlock_all();')
            if commit:
                self.commit()
            self.locks = {}
            return True
        except Exception as e:
            print(e)
            if commit:
                self.rollback()
            return False

    # ======================================================================

    def drop_queue(self, queue_schema=None, queue_table='global1'):
        full_table = f'"{queue_schema}"."{queue_table}"' if queue_schema else f'"{queue_table}"'
        sql = 'drop table if exists {full_table}'
        return self.execute_and_commit(sql)

    def ensure_queue(self, topics, queue_schema=None, queue_table='global1', return_cmd=False):

        full_table = f'"{queue_schema}"."{queue_table}"' if queue_schema else f'"{queue_table}"'

        sql = [f"""create table if not exists {full_table} (
  id          bigserial    PRIMARY KEY,
  eid         uuid NOT NULL,
  enqueued_at timestamp  NOT NULL DEFAULT current_timestamp,
  dequeued_at timestamp,
  action text,
  source text,
  topic       text         NOT NULL CHECK (length(topic) > 0),
  uid         bigint       NOT NULL,
  data        jsonb        NOT NULL,
  resp        jsonb,
  resp_at     timestamp
);"""]

        for topic in topics:
            sql.append(f"""create index if not exists priority_idx_{topic} on {full_table}
  (enqueued_at nulls first, topic)
where dequeued_at is null
      and resp is null
      and topic = '{topic}';""")
        sql = ''.join(sql)

        if return_cmd:
            return sql

        return self.execute_and_commit(sql)

    # =========================================================================

    def enqueue(self, topic, data, uid=None, action=None, source=None, returning='id', queue_schema=None,
                queue_table='global1', return_cmd=False):
        # put item - optionally source
        # INSERT INTO %(table)s (topic, data,) VALUES (%(name)s, $1) RETURNING id
        row = {'eid': uuid4(), 'topic': topic, 'data': data}
        if action: row['action'] = action
        if source: row['source'] = source
        if uid: row['uid'] = uid
        sql = self.insert_sql(queue_schema, queue_table, row, returning=returning)
        if return_cmd: return sql
        ret = self.fetch_and_commit(sql)
        try:
            if isinstance(returning, list):
                return ret[0]
            return ret[0][returning]
        except:
            return None

    def dequeue(self, topic, n=1, queue_schema=None, queue_table='global1', return_cmd=False):
        # pull n items from the queue TODO: support action filters
        full_table = f'"{queue_schema}"."{queue_table}"' if queue_schema else f'"{queue_table}"'
        sql = f"""WITH
  selected AS (
    SELECT * FROM {full_table}
    WHERE
      topic = '{topic}' AND
      dequeued_at IS NULL AND
      resp IS NULL
    ORDER BY id
    FOR UPDATE SKIP LOCKED
    LIMIT 1
  ),
  updated AS (
    UPDATE {full_table} AS t SET dequeued_at = current_timestamp
    FROM selected
    WHERE
      t.id = selected.id
    RETURNING t.data
  )
SELECT
  id,
  uid,
  (SELECT data::jsonb FROM updated),
  enqueued_at,
  action,
  source
FROM selected"""
        if return_cmd: return sql
        ret = self.fetch_and_commit(sql)
        return ret

    def replay_queue(self, topic, max_message_id, uid, queue_schema=None, queue_table='global1', return_cmd=False):
        full_table = f'"{queue_schema}"."{queue_table}"' if queue_schema else f'"{queue_table}"'
        sql = f"""WITH
  selected AS (
    SELECT * FROM {full_table}
    WHERE
      topic = '{topic}' AND
      id >= {max_message_id}
      and uid = {uid}
    ORDER BY id
    FOR UPDATE SKIP LOCKED
  )
SELECT
  id,
  uid,
  data::jsonb,
  enqueued_at,
  action,
  source
FROM selected"""
        if return_cmd: return sql
        ret = self.fetch_and_commit(sql)
        return ret

    def get_queue_response(self, qid, queue_schema=None, queue_table='global1', return_cmd=False, ):
        full_table = f'"{queue_schema}"."{queue_table}"' if queue_schema and self.dbtype == 'POSTGRES' else f'"{queue_table}"'
        sql = f'select "resp" from {full_table} where "id" = {self.pytype(qid)} and "resp" is not null'
        if return_cmd: return sql
        return self.fetch_and_commit(sql)

    def del_queue(self, qid, queue_schema=None, queue_table='global1', return_cmd=False):
        sql = self.delete_sql(queue_schema, queue_table, 'id', qid)
        if return_cmd: return sql
        return self.execute_and_commit(sql)

    def upd_queue(self, qid, resp, queue_schema=None, queue_table='global1', return_cmd=False):
        sql = self.update_sql(queue_schema, queue_table, {'resp': resp, 'resp_at': 'now()'}, 'id', qid)
        return self.execute_and_commit(sql)

    def ret_queue(self, qid, queue_schema=None, queue_table='global1'):
        # return the request to the queue
        sql = self.update_sql(queue_schema, queue_table, {'dequeued_at': None}, 'id', qid)
        if return_cmd: return sql
        return self.execute_and_commit(sql)

    def clear_queue(self, topic, queue_schema=None, queue_table='global1'):
        sql = self.delete_sql(queue_schema, queue_table, 'topic', topic)
        return self.execute_and_commit(sql)

    # select from queue for responses or deadletter


# =============================================================================

def init_db():
    if hasattr(init_db, 'db'):
        return init_db.db

    if settings:
        db_params = settings.DATABASES['default']
        host = db_params['HOST']
        port = int(db_params['PORT'])
        database = db_params['NAME']
        username = db_params['USER']
        passwd = db_params['PASSWORD']
    else:
        host = os.getenv('DB_HOST')
        port = int(os.getenv('DB_PORT'))
        database = os.getenv('DB_NAME')
        username = os.getenv('DB_USER')
        passwd = os.getenv('DB_PASSWORD')
    ret = DbAdaptor(host=host, port=port, database=database, username=username, password=passwd)
    init_db.db = ret
    return ret


# =============================================================================

if __name__ == "__main__":

    import os

    db = init_db()

    # test local cloud sql connection
    # db = DbAdaptor(host='127.0.0.1', port=5432, database='dev-pangea-db', username=settings.DB_USER, password=settings.DB_PASSWORD, autoconnect=False )
    # db = DbAdaptor(host='127.0.0.1', port=5432, database='dev-pangea-db', autoconnect=False )

    if True:  # queue test

        # dbensure_queue(['test1'])

        data = {'hello': 'world', 'foo': 1}
        x = db.enqueue('test1', data, source='api', action='create', returning=['id', 'eid'])
        # db.dequeue( 'test1', n=10, )

        # db.del_queue( 1 )
        # db.upd_queue( 1, data )
        # db.clear_queue( 'test1' )
