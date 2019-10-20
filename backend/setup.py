from setuptools import setup, find_packages
from configparser import ConfigParser
import json

config = ConfigParser()
config.read('Pipfile')
with open('Pipfile.lock', 'r') as f:
    locks = json.load(f)
install_requires = [
    name + locks['default'][name]['version']
    for name in config['packages'].keys()]
dev_requires = [
    name + locks['develop'][name]['version']
    for name in config['dev-packages'].keys()]

setup(
    name='penguin_judge',
    version='0.0.1',
    packages=find_packages(exclude=('tests',)),
    install_requires=install_requires,
    extras_require={'develop': dev_requires},
    package_data={'penguin_judge': ['schema.yaml']},
    entry_points={
        'console_scripts': [
            'penguin_judge=penguin_judge.main:main'
        ],
    }
)
