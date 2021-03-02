from setuptools import setup

setup(
    name='paratune',
    version='0.1',
    py_modules=['paratune'],
    install_requires=[
        'Click',
        'pysftp',
        'paramiko',
        'sshtunnel',
        'gitpython',
        'rq',
        'redis'
    ],
    entry_points='''
        [console_scripts]
        paratune=paratune.cli:main
    ''',
)