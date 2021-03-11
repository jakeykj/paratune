import os
import csv
import zlib

try:
    import pickle5 as pickle
except:
    import pickle

from uuid import uuid4
from redis import Redis

from .serializer import PickleFourSerializer
from .connections import connect_redis


def summarize_results(redis_host, redis_port, redis_password, job_name):
    redis = connect_redis(redis_host, redis_port, redis_password)
    all_results = []
    for key in redis.scan_iter("rq:job:%s:*" % job_name):
        rq_res = redis.hgetall(key)
        args = pickle.loads(zlib.decompress(rq_res[b'data']))
        if rq_res[b'status'] == b'failed':
            print('Failed job:')
            print(args)
            print(zlib.decompress(rq_res[b'exc_info']).decode('utf-8'))
            print('\n')
            continue
        res_dict = args[2][0]
        if b'result' in rq_res.keys():
            result = pickle.loads(rq_res[b'result'])
            if isinstance(result, dict):
                res_dict.update(result)
            else:
                res_dict['result'] = result
            all_results.append(res_dict)

    if len(all_results) == 0:
        print('No records found.')
    else:
        print('%d results fetched.' % len(all_results))
        with open('%s_summaries.csv' % job_name, 'w') as f:
            writer = csv.DictWriter(f, fieldnames=list(all_results[0].keys()))
            writer.writeheader()
            for data in all_results:
                writer.writerow(data)
        print('Results saved to %s_summaries.csv' % job_name)


def clear_queue_and_jobs(redis_host, redis_port, redis_password, job_name):
    redis = connect_redis(redis_host, redis_port, redis_password)
    for key in redis.scan_iter("rq:job:%s:*" % job_name):
        redis.delete(key)
    redis.srem('rq:queues', 'rq:queue:%s' % job_name)
    redis.delete('rq:finished:%s' % job_name)
    redis.delete('rq:failed:%s' % job_name)
