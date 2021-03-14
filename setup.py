import sys
from setuptools import setup

requirements = [
        'Click',
        'pysftp',
        'paramiko',
        'sshtunnel',
        'gitpython',
        'rq',
        'redis'
    ]

if sys.version_info.minor < 8:
    requirements.append('pickle5')

setup(
    name='paratune',
    version='0.1',
    py_modules=['paratune'],
    python_requires=">=3",
    install_requires=requirements,
    entry_points='''
        [console_scripts]
        paratune=paratune.cli:main
    ''',
)
