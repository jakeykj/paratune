import sys
sys.path.append('..')

from do_job import do_job

WORKER_FUNC = do_job

DEFAULT_ARGS = {
        'left': 1,
        'right': 1,
        'mul': 1
    }

FIXED_ARGS = {
    'name': 'test',
}

JOB_ARGS = [
    {
        'left': [1,2,3,4,5],
        'right': [6,7,8,9],
        'mul': [1,2]
    },
    {
        ('left', 'right'): [(1, 2), (3, 4)],
        'mul': [3, 4]
    }
]

REMOTES = {
    'user@jump1->jump2->target': '1234567'
}