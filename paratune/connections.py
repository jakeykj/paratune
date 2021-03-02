import os
from socket import socket
from getpass import getuser

import paramiko
import sshtunnel
from redis import Redis
from rq import Queue


LOCALHOST = '127.0.0.1'


class SSHConnection(object):
    def __init__(self, host_str, ssh_key_file) -> None:
        self.__tunnels = None
        self.__ports = None
        self.__ssh_client = None
        self.__sftp_client = None
        self.__ssh_host = None
        self.__ssh_port = None
        self.connect(host_str, ssh_key_file)
        
    @property
    def ssh(self):
        return self.__ssh_client
    
    @property
    def sftp(self):
        return self.__sftp_client
    
    @property
    def ssh_host(self):
        return self.__ssh_host
    
    @property
    def ssh_port(self):
        return self.__ssh_port
    
    def get_available_port(self, address):
        with socket() as s:
            s.bind((address, 0))
            return s.getsockname()[1]

    def resolve_host(self, host_str, default_user=None):
        if '@' in host_str:
            username, host_str = host_str.split('@')
        else:
            username = default_user or getuser()
        
        if ':' in host_str:
            host_str, ssh_port = host_str.split(':')
        else:
            ssh_port = 22
        
        return username, host_str, ssh_port

    def connect(self, host_str, ssh_key_file):
        if '->' in host_str:
            jump_hosts = host_str.split('->')
            ssh_tunnels, ports = [], []
            default_username = None
            for jump, target in zip(jump_hosts[:-1], jump_hosts[1:]):
                if len(ssh_tunnels) == 0:
                    username, jump_addr, ssh_port = self.resolve_host(jump, default_username)
                    default_username = username
                else:
                    username = getuser()
                    jump_addr, ssh_port = LOCALHOST, ports[-1]
                _, target_addr, target_port = self.resolve_host(target, default_username)

                tunnel_port = self.get_available_port(LOCALHOST)
                tunnel = sshtunnel.SSHTunnelForwarder(
                    jump_addr,
                    ssh_port=ssh_port,
                    ssh_username=username,
                    ssh_pkey=ssh_key_file,
                    remote_bind_address=(target_addr, target_port),
                    local_bind_address=(LOCALHOST, tunnel_port)
                )
                print('connecting tunnel:', jump, ssh_port)
                tunnel.start()
                ssh_tunnels.append(tunnel)
                ports.append(tunnel_port)
            username, ssh_address, ssh_port = getuser(), LOCALHOST, ports[-1]
            
            self.__tunnels = ssh_tunnels
            self.__ports = ports

        else:
            if '@' in host_str:
                username, ssh_address = host_str.split('@')
            else:
                username = getuser()
                ssh_address = host_str
            ssh_port = 22
        pkey = paramiko.RSAKey.from_private_key_file(ssh_key_file)
        self.__ssh_client = paramiko.SSHClient()
        self.__ssh_client.load_system_host_keys()
        self.__ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.__ssh_client.connect(hostname=ssh_address, port=ssh_port, username=username, pkey=pkey)
        self.__ssh_host = ssh_address
        self.__ssh_port = ssh_port

        self.__sftp_client = paramiko.SFTPClient.from_transport(self.__ssh_client.get_transport())


def connect_redis(redis_host, redis_port, redis_password):
    redis = Redis(redis_host, redis_port, password=redis_password)
    return redis

def get_redis_queue(queue_name, redis_host, redis_port, redis_password):
    redis = connect_redis(redis_host, redis_port, redis_password)
    assert redis.ping(), 'Failed to connect Redis.'
    queue = Queue(queue_name, connection=redis)
    return redis, queue

if __name__ == '__main__':
    conn = SSHConnection()
    conn.connect('user@jump1->jump2->target', os.path.expanduser('~/.ssh/id_rsa'))

    stdin, stdout, stderr = conn.ssh.exec_command('ls')
    stdout=stdout.readlines()
    print(stdout)