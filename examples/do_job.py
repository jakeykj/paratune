import time


def do_job(args):
    time.sleep(0.2)
    return args['left'] + args['mul'] * args['right']