#!/usr/bin/env python

from hashlib import pbkdf2_hmac
from getpass import getpass
import secrets
import sys
import os
import psycopg2
from psycopg2.extensions import parse_dsn


def _kdf(password: str, salt: bytes) -> bytes:
    return pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)


#dburl = "postgresql://user:password@localhost:5432/penguin_judge"
db_url = os.getenv("PENGUIN_DB_URL")

if (db_url == None):
    print("Set env PENGUIN_DB_URL")
    exit(1)

if (len(sys.argv) != 2):
    print("Usage: %s <target_login_id>" % sys.argv[0])
    exit(1)

db_opts = parse_dsn(db_url)
target_login_id = sys.argv[1]
new_password = getpass(prompt='New Password: ')
salt = secrets.token_bytes()
hashed_pw = _kdf(new_password, salt)

#print("db_url", db_url)
#print("target_login_id", target_login_id)
#print("new_password", new_password)
#print("salt", salt)
#print("hashed_pw", hashed_pw)
#print("db user", db_opts['user'])
#print("db password", db_opts['password'])
#print("db host", db_opts['host'])
#print("db dbname", db_opts['dbname'])


conn = psycopg2.connect(user = db_opts['user'], host = db_opts['host'], password = db_opts['password'], dbname = db_opts['dbname'])
cur = conn.cursor()
cur.execute("SELECT login_id from users WHERE login_id = %s;", [target_login_id])
fetched = cur.fetchone()
if (fetched == None):
    print("No such user:", target_login_id)
    exit(1)

cur.execute("UPDATE users SET salt = %s, password = %s WHERE login_id = %s;", [salt, hashed_pw, target_login_id])
conn.commit()
cur.close()
conn.close()
