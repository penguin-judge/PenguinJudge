from setuptools import setup, find_packages
from configparser import ConfigParser
import json

config = ConfigParser()
config.read('Pipfile')
packages = list(config['packages'].keys())
with open('Pipfile.lock', 'r') as f:
    pipenv_locks = json.load(f)['default']
install_requires = [
    name + pipenv_locks[name]['version']
    for name in packages
]

setup(
    name='penguin_judge',
    version='0.0.1',
    packages=find_packages(),
    install_requires=install_requires,
    entry_points={
        'console_scripts': [
            'penguin_judge=penguin_judge.main:main'
        ],
    }
)
