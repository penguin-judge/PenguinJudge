import json
from typing import NamedTuple, Optional

import common


class Environment(NamedTuple):
    name: Optional[str]
    test_image_name: Optional[str]
    compile_image_name: Optional[str]


ENVIRONMENTS = [
    Environment('C (gcc 8.2)', 'penguin_judge_c_judge:8.2', 'penguin_judge_c_compile:8.2'),
    Environment('C++ (gcc 8.2)', 'penguin_judge_cpp_judge:8.2', 'penguin_judge_cpp_compile:8.2'),
    Environment('Python (3.7)', 'penguin_judge_python:3.7', None),
    Environment('PyPy3.6 (7.2.0)', 'penguin_judge_pypy3.6:7.2.0', None),
    Environment('Ruby (2.6.5)', 'penguin_judge_ruby:2.6.5', None),
    Environment('Go (1.13.4)', 'penguin_judge_go_judge:1.13.4', 'penguin_judge_go_compile:1.13.4'),
    Environment('Java (OpenJDK 14)', 'penguin_judge_java_judge:14', 'penguin_judge_java_compile:14'),
    Environment('Node (12.13.0)', 'penguin_judge_node:12.13.0', None),
    Environment('Rust (1.39.0)', 'penguin_judge_rust_judge:1.39.0', 'penguin_judge_rust_compile:1.39.0'),
]

items = {}
for e in ENVIRONMENTS:
    items[e.name] = dict(
        name=e.name, test_image_name=e.test_image_name,
        active=True, published=True)
    if e.compile_image_name:
        items[e.name]['compile_image_name'] = e.compile_image_name

try:
    common.login()
    for e in common.get('/environments').json():
        items.pop(e['name'], None)

    for _, e in items.items():
        r = common.post_json('/environments', e)
        assert r.status_code == 200
finally:
    common.logout()
