import os
from socket import gethostname

# redis configurations
REDIS_HOST = 'localhost'
REDIS_PORT = os.environ.get('REDIS_PORT', 6379)
REDIS_PASSWORD = os.environ['REDIS_PASSWORD']

# paratune configurations
REMOTES = [
    'user@jump1->jump2->target',
    'user@jump->user@target'
]
SSH_KEY = os.path.expanduser('~/.ssh/id_rsa')

REMOTE_DIR = 'fun/examples'
MK_SUBFOLDERS = [
    'a/b',
    'a/c',
    'a/d'
]

UPLOAD_EXCLUDES = [
    'a',
    '*.git*',
    '*__pycache__'
]
