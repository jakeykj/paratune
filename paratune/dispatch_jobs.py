import os
from copy import deepcopy
from itertools import product
from itertools import chain
import inspect

from uuid import uuid4
from redis import Redis, connection
from rq import Queue
from rq.job import Job
import git

from .serializer import PickleFourSerializer
from .connections import SSHConnection, get_redis_queue


def dispatch_jobs(redis_host, redis_port, redis_password, job_configs, job_name):
    redis, queue = get_redis_queue(job_name, redis_host, redis_port, redis_password)
    try:
        try:
            repo = git.Repo('.', search_parent_directories=False)
            changed = [x.a_path for x in repo.index.diff(None)]
            untracked = [x for x in repo.untracked_files]
            if len(changed) > 0 or len(untracked) > 0:
                if len(changed) > 0:
                    print('Uncommitted changes deteched:')
                    for item in changed:
                        print('\t'+item)
                if len(untracked) > 0:
                    print('Untracked files deteched:')
                    for item in untracked:
                        print('\t'+item)
                print('\n\nSumamry: %d untracked files and %d unstaged files.' % (len(untracked), len(changed)))
                if input('It is recommended to commit any changes before'
                         ' dispatching jobs\nto track git commit hash in'
                         ' experiments.\nDo you want to proceed anyway?'
                         ' (May results in inaccurate git hash recorded.)\n'
                         'Y/[N]>>').lower() not in ['y', 'yes']:
                    print('dispatch canceled.')
                    redis.close()
                    return 0
            git_hash = repo.git.rev_parse(repo.head.commit.hexsha, short=6)
        except git.InvalidGitRepositoryError:
            if input('Not a git repository. It is recommended to use'
                    ' git to manage the project. Do you want to proceed'
                    ' anyway?\nY/[N]>>').lower() not in ['y', 'yes']:
                print('dispatch canceled.')
                redis.close()
                return 0
        print('git checked')
        n_jobs = 0
        print(job_configs)
        for args_group in job_configs['JOB_ARGS']:
            # create configs
            single_args = {k: v for k, v in args_group.items() if not isinstance(k, tuple)}
            tupled_args = {k: v for k, v in args_group.items() if isinstance(k, tuple)}
            
            names, param_groups = zip(*single_args.items())
            param_groups = list(product(*param_groups))
            
            tupled_args_grid = []
            for keys, values in tupled_args.items():
                tupled_args_grid.append([[(k, v) for k, v in zip(keys, params)] 
                                        for params in values])
            tupled_args_grid = list(product(*tupled_args_grid))
            tupled_args_grid = [dict(chain(*cell)) for cell in tupled_args_grid]
            
            
            for params in param_groups:
                for tupled_cell in tupled_args_grid:
                    # load default configs
                    args = deepcopy(job_configs.get('DEFAULT_ARGS', dict()))
                    args.update(job_configs.get('FIXED_ARGS', dict()))
                    args.update(tupled_cell)
                    args.update({k: v for k, v in zip(names, params)})
                    
                    args['git_commit'] = git_hash
                    
                    job = Job.create(job_configs['WORKER_FUNC'], args=(args,), 
                                    timeout=job_configs.get('TIMEOUT', '24h'),
                                    result_ttl=job_configs.get('RESULTS_TTL', -1),
                                    serializer=PickleFourSerializer,
                                    connection=redis,
                                    id=job_name+':'+str(uuid4()))
                    queue.enqueue_job(job)
                    n_jobs += 1
        print(f'Enqueued {n_jobs} jobs.')
        return n_jobs

    finally:
        redis.close()


def start_remote(remotes, ssh_key_file, remote_dir, rq_config, job_name):
    for host_str, devs in remotes.items():
        for dev in list(devs):
            envs = "source ~/.bashrc; "
            envs += "export CUDA_VISIBLE_DEVICES=%s; " % dev
            envs += "export OMP_NUM_THREADS=1;"

            chdir = "cd ~/%s;" % remote_dir
            tunnel_cmd = "build_tunnel;"
            rq_command = "nohup sh -c 'rq worker %s -c %s --burst;'" % (job_name, rq_config)
            redirction = "> /dev/null 2>&1 &"
            
            command = ' '.join([envs, chdir, tunnel_cmd, rq_command, redirction])
            
            client = SSHConnection(host_str, ssh_key_file)
            transport = client.ssh.get_transport()
            channel = transport.open_session()
            
            print('Executing command on remote %s' % host_str)
            print(command)
            channel.exec_command(command)

            client.ssh.close()