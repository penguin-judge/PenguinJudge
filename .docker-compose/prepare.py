from configparser import ConfigParser
import os
import time
from urllib.parse import urlsplit, urlunsplit
import sys
import subprocess

import pika
import psycopg

WD = os.path.dirname(os.path.abspath(__file__))
PENGUIN_JUDGE_ALEMBIC_CMD = ['penguin_judge', 'alembic', '-c', os.path.join(WD, 'config.ini')]


def _run_alembic_migration() -> None:
    subprocess.run(PENGUIN_JUDGE_ALEMBIC_CMD + ['upgrade', 'head'])


def _wait_alembic_migration() -> None:
    ret = subprocess.run(PENGUIN_JUDGE_ALEMBIC_CMD + ['heads'], capture_output=True, encoding='utf8')
    head_rev = ret.stdout[:ret.stdout.find(' ')]
    while True:
        ret = subprocess.run(PENGUIN_JUDGE_ALEMBIC_CMD + ['current'], capture_output=True, encoding='utf8')
        if ret.stdout.startswith(head_rev):
            print('database schema upgraded')
            break
        print('.', end='', flush=True)
        time.sleep(0.01)


def _wait(msg, try_func, *, ignore_retry=None,
          update_func=None, ignore_update_retry=None):
    print('checking {}'.format(msg), end='', flush=True)
    while True:
        try:
            try_func()
            break
        except KeyboardInterrupt:
            return
        except Exception as e:
            if ignore_retry and ignore_retry(e):
                break
            print('.', end='', flush=True)
            time.sleep(0.01)
        if not update_func:
            continue
        try:
            update_func()
            print(' [created]')
            return
        except Exception as e:
            if ignore_update_retry and ignore_update_retry(e):
                print(' [created by another process]')
                return
            print('.', end='', flush=True)
            time.sleep(0.01)
    print(' [ok]', flush=True)


def main():
    migration_mode = None
    if len(sys.argv) > 1:
        if sys.argv[1] == 'run_migration':
            migration_mode = 'run'
        elif sys.argv[1] == 'wait_migration':
            migration_mode = 'wait'

    config = ConfigParser()
    with open(os.path.join(WD, 'config.ini'), 'r') as f:
        config.read_file(f)

    db_url = config.defaults()['sqlalchemy.url']
    parts = urlsplit(db_url)
    new_netloc = 'postgres:password@' + parts[1].split('@')[1]
    db_user_url = urlunsplit(('postgres',) + parts[1:2] + ('/postgres', '', ''))
    db_admin_url = urlunsplit(('postgres', new_netloc,) + ('', '', ''))
    mq_url = config.defaults()['mq.url']
    mq_params = pika.connection.URLParameters(mq_url)

    # MQが繋がるまで待つ
    def _mq_try_connect():
        pika.BlockingConnection(mq_params).close()
    _wait('mq', _mq_try_connect)

    # DBに繋がるまで待つ
    def _db_try_connect():
        with psycopg.connect(db_admin_url) as c, c.cursor():
            return

    def _db_not_refused(e):
        if isinstance(e, psycopg.OperationalError):
            msg = str(e)
            return 'Connection refused' not in msg
        return False
    _wait('db connectivity', _db_try_connect, ignore_retry=_db_not_refused)

    # DBのロール有無の確認
    def _db_check_role():
        with psycopg.connect(db_user_url):
            return

    def _db_create_role():
        with psycopg.connect(db_admin_url) as c, psycopg.ClientCursor(c) as cur:
            cur.execute(f'CREATE ROLE {parts.username} WITH LOGIN PASSWORD %s', (parts.password,))

    def _db_already_exists(e):
        return 'already exists' in str(e)
    _wait('db role', _db_check_role, update_func=_db_create_role,
          ignore_update_retry=_db_already_exists)

    # DBのDatabase有無の確認
    def _db_check_db():
        with psycopg.connect(db_url):
            return

    def _db_create_db():
        with psycopg.connect(db_admin_url) as c, psycopg.ClientCursor(c) as cur:
            c.autocommit = True
            cur.execute('CREATE DATABASE {} OWNER {}'.format(
                parts.path[1:], parts.username))
    _wait('db database', _db_check_db, update_func=_db_create_db,
          ignore_update_retry=_db_already_exists)

    if migration_mode:
        if migration_mode == 'run':
            _run_alembic_migration()
        elif migration_mode == 'wait':
            _wait_alembic_migration()

    print('[PREPARE FINISHED]')


if __name__ == '__main__':
    main()
