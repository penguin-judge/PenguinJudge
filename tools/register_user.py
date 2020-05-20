import csv
from typing import NamedTuple
import os
import sys

import common

NAME_COLUMN = 1
MAIL_COLUMN = 4


class UserEntry(NamedTuple):
    name: str
    email: str


def main(csv_path: str) -> None:
    password_suffix = os.environ['PASSWORD_SUFFIX']

    with open(csv_path, newline='') as csvfile:
        dialect = csv.Sniffer().sniff(csvfile.read())
        csvfile.seek(0)
        reader = csv.reader(csvfile, dialect)
        header = next(reader)
        if header[NAME_COLUMN] != 'お名前' or header[MAIL_COLUMN] != 'メールアドレス':
            raise Exception('invalid csv')
        users = [UserEntry(row[NAME_COLUMN], row[MAIL_COLUMN]) for row in reader]
        del reader

    invalid_domains = set([u for u in users if '@' not in u.email])
    if invalid_domains:
        print('FOUND INVALID E-MAIL ADDRS')
        for u in invalid_domains:
            print(u)
        return

    common.login()
    try:
        for u in users:
            password = u.email[:u.email.index('@') + 1] + password_suffix
            r = common.register(u.email, u.name, password, ignore_error=True)
            if r.status_code == 201:
                print('[OK] {}: {} ({})'.format(u.email, u.name, password))
            elif r.status_code == 409:
                print('[SKIP] {}: {} ({})'.format(u.email, u.name, password))
            else:
                print('[ERROR] {}: {} ({})'.format(u.email, u.name, password))
                print(r.status_code)
                print(r.json())
                raise
    finally:
        common.logout()


if __name__ == '__main__':
    if len(sys.argv) == 1:
        print('usage: {} <csv path>'.format(sys.argv[0]))
        sys.exit()
    main(sys.argv[1])
