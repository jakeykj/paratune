import os
import sys
import paramiko
import subprocess
from .connections import SSHConnection

def mkdir_p(sftp, remote_directory):
    """Change to this directory, recursively making new folders if needed.
    Returns True if any folders were created."""
    if remote_directory == '/':
        # absolute path so change directory to root
        sftp.chdir('/')
        return
    if remote_directory == '':
        # top-level relative directory must exist
        return
    try:
        sftp.chdir(remote_directory) # sub-directory exists
    except FileNotFoundError:
        dirname, basename = os.path.split(remote_directory.rstrip('/'))
        mkdir_p(sftp, dirname) # make parent directories
        sftp.mkdir(basename) # sub-directory missing, so created it
        sftp.chdir(basename)
        return True


def run_rsync_command(command):
    print('Running command:',  command, end='\n\n')
    p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()

    if stdout == "":
        print(stderr.decode())
        raise RuntimeError('Failed to upload file, error message from shell:')
    else:
        print(stdout.decode())


def upload_to_remote(ssh_connect, remote_dir, sub_dirs, upload_excluded=None, delete=False):
    # change to remote dir, create if does not exist
    mkdir_p(ssh_connect.sftp, remote_dir)

    # upload files
    command = ["rsync", "-ahP"]
    if ssh_connect.ssh_port != 22:
        command += ["-e", "'ssh -p %d -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null'" % ssh_connect.ssh_port]

    if upload_excluded is not None:
        for item in upload_excluded:
            command += ["--exclude", "'%s'" % item]

    # source & remote
    command += ["."];
    command += ["%s:~/%s" % (ssh_connect.ssh_host, remote_dir)]
    if delete:
        command += ["--delete"]
    command = ' '.join(command)

    if delete:
        # list out changes first and ask for confirmation
        run_rsync_command(command+' --dry-run')
        if input('This command will potentially delete files from the remote host, \n'
                 'please confirm the above file changes. Y/[N]>').lower() not in ['y', 'yes']:
            print('File uploading canceled.')
            return

    run_rsync_command(command)

    # create required subdirectoris
    for subdir in sub_dirs:
        ssh_connect.sftp.chdir(None)
        mkdir_p(ssh_connect.sftp, remote_dir+'/'+subdir)