import os
import sys
from nproxypool.utils.run import run_pool, run_server, run_generate


def show_usage():
    print('usage:')
    print('mypool gen:        to generate a new proxypool project.')
    print('mypool run_pool:   to run the proxypool.')
    print('mypool run_server: to run server for the proxypool.')
    sys.exit(1)


def execute():
    args = sys.argv[1:]
    if not args:
        show_usage()
    dir = os.path.abspath('.')
    cmdname = args[0]
    if cmdname == 'gen':
        if len(args) > 1:
            name = args[1]
        else:
            name = 'proxypool'
        run_generate(dir, name=name)
    elif cmdname == 'run_pool':
        run_pool(dir)
    elif cmdname == 'run_server':
        run_server(dir)
    else:
        show_usage()
