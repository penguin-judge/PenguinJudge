from configparser import ConfigParser
import os
import time
from urllib.parse import urlsplit, urlunsplit

import pika
import psycopg2

WD = os.path.dirname(os.path.abspath(__file__))


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
    config = ConfigParser()
    with open(os.path.join(WD, 'config.ini'), 'r') as f:
        config.read_file(f)

    db_url = config.defaults()['sqlalchemy.url']
    parts = urlsplit(db_url)
    new_netloc = 'postgres:password@' + parts[1].split('@')[1]
    db_user_url = urlunsplit(parts[0:2] + ('/postgres', '', ''))
    db_admin_url = urlunsplit(parts[0:1] + (new_netloc,) + ('', '', ''))
    mq_url = config.defaults()['mq.url']
    mq_params = pika.connection.URLParameters(mq_url)

    # MQが繋がるまで待つ
    def _mq_try_connect():
        pika.BlockingConnection(mq_params).close()
    _wait('mq', _mq_try_connect)

    # DBに繋がるまで待つ
    def _db_try_connect():
        with psycopg2.connect(db_admin_url) as c, c.cursor():
            return

    def _db_not_refused(e):
        if isinstance(e, psycopg2.OperationalError):
            msg = str(e)
            return 'Connection refused' not in msg
        return False
    _wait('db connectivity', _db_try_connect, ignore_retry=_db_not_refused)

    # DBのロール有無の確認
    def _db_check_role():
        with psycopg2.connect(db_user_url):
            return

    def _db_create_role():
        with psycopg2.connect(db_admin_url) as c, c.cursor() as cur:
            cur.execute('CREATE ROLE {} WITH LOGIN PASSWORD %s'.format(
                parts.username), (parts.password,))

    def _db_already_exists(e):
        return 'already exists' in str(e)
    _wait('db role', _db_check_role, update_func=_db_create_role,
          ignore_update_retry=_db_already_exists)

    # DBのDatabase有無の確認
    def _db_check_db():
        with psycopg2.connect(db_url):
            return

    def _db_create_db():
        with psycopg2.connect(db_admin_url) as c, c.cursor() as cur:
            c.autocommit = True
            cur.execute('CREATE DATABASE {} OWNER {}'.format(
                parts.path[1:], parts.username))
    _wait('db database', _db_check_db, update_func=_db_create_db,
          ignore_update_retry=_db_already_exists)
    print('[PREPARE FINISHED]')


if __name__ == '__main__':
    main()
