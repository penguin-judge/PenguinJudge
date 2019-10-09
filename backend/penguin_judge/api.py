import os.path
from typing import Any

from flask import Flask, current_app


def _detect_static_dir() -> str:
    cands = [
        os.path.abspath(os.path.join(
            os.path.dirname(__file__), '../../frontend')),
        os.getcwd(),
    ]
    for c in cands:
        if os.path.isfile(os.path.join(c, 'index.html')):
            return c + '/'
    raise Exception('cannot detect static directory path')


app = Flask(__name__, static_folder=_detect_static_dir())


@app.route('/')
def index() -> Any:
    print(os.getpid())
    return current_app.send_static_file('index.html')


if __name__ == '__main__':
    print(app.url_map)
    app.run()
