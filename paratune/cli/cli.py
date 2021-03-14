import functools
import importlib
from functools import update_wrapper
from paratune.connections import SSHConnection
from paratune.upload_files import upload_to_remote
from paratune.dispatch_jobs import dispatch_jobs, start_remote
from paratune.summarize_results import summarize_results, clear_queue_and_jobs


import click
import sys
from paratune import VERSION



def common_params(func):
    @click.option('--config', '-c', envvar='PT_CONFIG',
                  default='pt_config',
                  help='Module containing PARATUNE settings.')
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper


def load_config(module, path_='.'):
    """Reads all UPPERCASE variables defined in the given module file."""
    sys.path.append(path_)
    settings = importlib.import_module(module)
    return {k: v for k, v in settings.__dict__.items() if k.upper() == k}


@click.group()
@click.version_option(VERSION)
def main():
    """PARATUNE: a tool for parameter tuning with RQ."""
    pass


@main.command()
@common_params
@click.option('--delete', is_flag=True, 
              help='Delete remote files if they do not exist at the source.')
@click.option('--remote', type=str,
              help='Destination of files. Example: user@jump:22->user@host:22')
def upload(**options):
    settings = load_config(options['config'])
    if options['remote'] is not None:
        remotes = [options['remote']]
    else:
        remotes = settings['REMOTES']

    for remote in remotes:
        click.echo(f'Uploading to server {remote}...')
        conn = SSHConnection(remote, settings['SSH_KEY'])
        upload_to_remote(conn, settings['REMOTE_DIR'], 
                         sub_dirs=settings.get('MK_SUBFOLDERS', []),
                         upload_excluded=settings.get('UPLOAD_EXCLUDES', []),
                         delete=options.get('delete', False))
        

def configure_jobs(func):
    @click.argument('jobs', type=str)
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

def parse_job_configs(options):
    *path_, job_module = options['jobs'].split('/')
    path_ = '/'.join(path_)
    job_options = load_config(job_module, path_)
    return job_options, job_module


@main.command()
@common_params
@click.argument('jobs', type=str)
def dispatch(**options):
    project_settings = load_config(options['config'])
    job_options, job_name = parse_job_configs(options)
    n_jobs = dispatch_jobs(project_settings['REDIS_HOST'], 
                           project_settings['REDIS_PORT'], 
                           project_settings['REDIS_PASSWORD'], 
                           job_options, job_name)
    if n_jobs > 0 and 'REMOTES' in project_settings.keys():
        rq_config = options['config']
        start_remote(job_options['REMOTES'], project_settings['SSH_KEY'], project_settings['REMOTE_DIR'], rq_config, job_name)
    
    
@main.command()
@common_params
@click.argument('jobs', type=str)
@click.option('--remotes', type=str)
def remoteworker(**options):
    project_settings = load_config(options['config'])
    job_options, job_name = parse_job_configs(options)
    ssh_key_file = project_settings['SSH_KEY']
    if options['remotes'] is None:
        remotes = job_options['REMOTES']
    else:
        remotes = {options['remotes'].split(':')[0]: options['remotes'].split(':')[1]}
    start_remote(remotes, ssh_key_file, project_settings['REMOTE_DIR'], options['config'], job_name)


@main.command()
@common_params
@click.argument('job_name', type=str)
def summarize(**options):
    project_settings = load_config(options['config'])
    # job_options, job_name = parse_job_configs(options)
    summarize_results(project_settings['REDIS_HOST'], project_settings['REDIS_PORT'], project_settings['REDIS_PASSWORD'], 
                      options['job_name'])


@main.command()
@common_params
@click.argument('jobs', type=str)
def clear(**options):
    project_settings = load_config(options['config'])
    job_options, job_name = parse_job_configs(options)
    clear_queue_and_jobs(project_settings['REDIS_HOST'], project_settings['REDIS_PORT'], project_settings['REDIS_PASSWORD'], 
                         job_name)


if __name__ == '__main__':
    dispatch()