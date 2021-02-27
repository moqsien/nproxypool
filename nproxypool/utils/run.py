# ===========================
# run pool or server
# ===========================
import nproxypool
import os
import sys
import time
import signal
import traceback
import importlib
from copy import deepcopy
from multiprocessing import Process
from werkzeug.debug import DebuggedApplication
from nproxypool.base.verifier import run_verifier
from nproxypool.base.synchronizer import sync
from nproxypool.base.proxy_fetcher import ProxyFetcherBase
from nproxypool.utils.misc import get_redis_config, get_verifier_config
from nproxypool.utils.misc import get_sychronizer_config, get_fetcher_config
from nproxypool.utils.misc import get_logfile_dir, get_gunicorn_config
from nproxypool.utils.misc import GunicornStandalone
from nproxypool.base.server import make_app
from nproxypool.base.logger import get_logger
from nproxypool.utils.misc import copytree


# close subprocess when parent process is closed
def term(sig_num, addtion):
    print('term current pid is %s, group id is %s' % (os.getpid(), os.getpgrp()))
    os.killpg(os.getpgid(os.getpid()), signal.SIGKILL)


signal.signal(signal.SIGTERM, term)
print('master pid is %s' % os.getpid())


def run_fetcher(**kwargs):
    file_dir = kwargs.get('log_file_path')
    logger = get_logger(
        name='fetcher',
        filename='fetcher.log',
        filedir=file_dir,
        level='warning',
        back_count=7
    )
    to_sleep = kwargs.get('to_sleep', 30)
    fetcher_module = importlib.import_module('my_fetcher')
    for attr in dir(fetcher_module):
        v = getattr(fetcher_module, attr)
        if type(v).__name__ == 'type' and issubclass(v, ProxyFetcherBase) and attr != 'ProxyFetcherBase':
            try:
                fetcher = v(**kwargs)
                fetcher.run()
            except:
                logger.error(str(traceback.format_exc()))
    time.sleep(to_sleep)


def run_pool(dir):
    """
    dir: project dir
    """
    if dir not in sys.path:
        sys.path.append(dir)
    redis_params = get_redis_config(dir)
    log_file_dir = get_logfile_dir(dir)

    # fetcher process
    kwargs_fetcher = get_fetcher_config(dir)
    kwargs_fetcher.update(redis_params)
    kwargs_fetcher['log_file_path'] = log_file_dir
    p = Process(target=run_fetcher, kwargs=kwargs_fetcher)
    p.daemon = True
    p.start()

    # verifier processes
    verifier_conf_list = get_verifier_config(dir)
    for verifier_conf in verifier_conf_list:
        kwargs_v = deepcopy(verifier_conf)
        kwargs_v.update(redis_params)
        kwargs_v['log_file_path'] = log_file_dir
        t = Process(target=run_verifier, kwargs=kwargs_v)
        t.daemon = True
        t.start()

    # synchronizer process
    kwargs_sync = get_sychronizer_config(dir)
    kwargs_sync['log_file_path'] = log_file_dir
    p1 = Process(target=sync, kwargs=kwargs_sync)
    p1.daemon = True
    p1.start()

    while True:
        time.sleep(1)


def run_server(dir):
    options = get_gunicorn_config(dir)
    app = make_app(dir)
    if options.get('debug'):
        options["workers"] = 1
        app.wsgi_app = DebuggedApplication(app.wsgi_app, True)
        print(' * Launching in DEBUG mode')
        print(' * Serving Flask using a single worker "{}"'.format(app.import_name))
        options["reload"] = bool(options['debug'])
    else:
        print(' * Launching in Production Mode')
        print(' * Serving Flask with {} worker(s) "{}"'.format(
            options["workers"], app.import_name
        ))
    server = GunicornStandalone(app, options=options)
    server.run()


def run_generate(dir, name='proxypool'):
    tempfile_path = os.path.join(
        os.path.dirname(nproxypool.__file__),
        'templates/pool'
    )
    copytree(tempfile_path, os.path.join(dir, name))
