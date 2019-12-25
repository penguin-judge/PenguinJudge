import datetime
import json
import os
from os.path import join
import sys
import math
import re
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED

import common


def _try_parse_num(x):
    try:
        return float(x)
    except:
        return math.inf


base_path = os.path.abspath(sys.argv[1])
contest_id = os.path.basename(base_path)
today = datetime.date.today()
contest_start = datetime.datetime(
    today.year, today.month, today.day,
    tzinfo=datetime.timezone(datetime.timedelta(hours=9), name='JST'))
contest_end = contest_start + datetime.timedelta(hours=1)
with open(join(base_path, 'README.md'), 'r', encoding='utf8') as f:
    contest_desc = f.readlines()
    contest_title = contest_desc[0].strip().lstrip('# ')

if len(contest_desc) >= 3:
    try:
        s, e = contest_desc[2].strip().split(' - ')
        contest_start = datetime.datetime.fromisoformat(s)
        contest_end = datetime.datetime.fromisoformat(e)
        del contest_desc[2]
    except Exception:
        pass


def _parse_problem_info(l):
    TABLE = [
        ('memory_limit', ('メモリ', 'mem')),
        ('time_limit', ('時間', 'time')),
        ('score', ('配点', 'スコア', 'score')),
    ]
    ret = {}
    items = [[y.strip() for y in x.strip().split(':')] for x in l.split('/')]
    for n, v in items:
        k, n = None, n.lower()
        for kk, patterns in TABLE:
            for pattern in patterns:
                if pattern in n:
                    k = kk
                    break
            if k:
                break
        if k:
            m = re.match(r'[0-9]+', v)
            if m:
                ret[k] = int(m.group(0))
    return ret


problems = []
for dir_name in os.listdir(base_path):
    p_path = join(base_path, dir_name)
    readme_path = join(p_path, 'README.md')
    if not os.path.isfile(readme_path):
        continue
    p = dict(id=dir_name, time_limit=10, memory_limit=512, score=100)
    with open(readme_path, 'r', encoding='utf8') as f:
        p['title'] = f.readline().strip().lstrip('# ')
        problem_desc = f.readlines()
    try:
        p.update(_parse_problem_info(problem_desc[1]))
        del problem_desc[1]
    except Exception:
        pass
    p['description'] = ''.join(problem_desc).strip()

    inputs = [
        x[:-3] for x in os.listdir(join(p_path, 'input'))
        if x.endswith('.in')]
    outputs = [
        x[:-4] for x in os.listdir(join(p_path, 'output'))
        if x.endswith('.out')]
    io_names = sorted(set(inputs) & set(outputs), key=lambda x: (_try_parse_num(x), x))

    zip_bytes = BytesIO()
    with ZipFile(zip_bytes, mode='w', compression=ZIP_DEFLATED) as z:
        for io_name in io_names:
            in_bytes = open(join(p_path, 'input', io_name + '.in'), 'rb').read()
            out_bytes = open(join(p_path, 'output', io_name + '.out'), 'rb').read()
            with z.open(io_name + '.in', mode='w') as f:
                f.write(in_bytes)
            with z.open(io_name + '.out', mode='w') as f:
                f.write(out_bytes)
    p['dataset'] = zip_bytes.getvalue()
    problems.append(p)


def _register_contest():
    url, method = '/contests', common.post_json
    for x in common.get('/contests').json():
        if x['id'] == contest_id:
            print('[contest] 既に登録済みなのでPATCHで更新します')
            url = '/contests/' + contest_id
            method = common.patch_json
            break
    body = {
        'id': contest_id,
        'title': contest_title,
        'description': ''.join(contest_desc).strip(),
        'start_time': contest_start.isoformat(),
        'end_time': contest_end.isoformat(),
    }
    r = method(url, body)
    print('[contest] http {}'.format(r.status_code))
    assert r.status_code == 200


def _register_problem(p):
    url = '/contests/' + contest_id + '/problems'
    method = common.post_json
    for x in common.get(url).json():
        if x['id'] == p['id']:
            print('[problem {}] 既に登録済みなのでPATCHで更新します'.format(p['id']))
            url += '/' + p['id']
            method = common.patch_json
            break
    body = dict(p)
    body.pop('dataset')
    r = method(url, body)
    print('[problem] http {}'.format(r.status_code))
    assert r.status_code in (200, 201)
    r = common.upload_test_dataset(contest_id, p['id'], p['dataset'])
    print('[problem] dataset http {}'.format(r.status_code))
    assert r.status_code == 200

try:
    common.login()
    _register_contest()
    for p in problems:
        _register_problem(p)
finally:
    common.logout()
