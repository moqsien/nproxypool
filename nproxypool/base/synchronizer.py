# ========================================================
# automatically remove proxies exist in second-level pools
# but not in the first-level one
# ========================================================
import time
import traceback
from nproxypool.base.db import RedisPool
from nproxypool.base.logger import get_logger


class Synchronizer(object):
    def __init__(self):
        self._first_level_pool = None
        self._second_level_pool = None
        self._second_level_pool_keys = []

    def init_sync(self, **kwargs):
        host = kwargs.get('host', 'localhost')
        port = kwargs.get('port', 6379)
        password = kwargs.get('password', '654321')
        first_db = kwargs.get('first_db', 0)
        second_db = kwargs.get('second_db', 1)
        second_db_keys = kwargs.get('second_db_keys', [])

        first_db_param = {
            'host': host,
            'port': port,
            'password': password,
            'db': first_db
        }
        second_db_param = {
            'host': host,
            'port': port,
            'password': password,
            'db': second_db
        }
        self._second_level_pool_keys = second_db_keys
        self._first_level_pool = RedisPool(**first_db_param)
        self._second_level_pool = RedisPool(**second_db_param)

    def synchronize(self, **kwargs):
        self.init_sync(**kwargs)
        first_level_pool_proxies = self._first_level_pool.get_all()
        for key in self._second_level_pool_keys:
            proxies_in_second_key = self._second_level_pool.z_get_all(key)
            for proxy in proxies_in_second_key:
                if proxy not in first_level_pool_proxies:
                    if isinstance(proxy, bytes):
                        proxy = str(proxy, encoding='utf-8')
                    print("!!!remove proxy: {}".format(proxy))
                    self._second_level_pool.z_delete(proxy, key)


def sync(**kwargs):
    to_sleep = kwargs.get('to_sleep', 300)
    file_dir = kwargs.get('log_file_path')
    logger = get_logger(
        name='synchronizer',
        filename='synchronizer.log',
        filedir=file_dir,
        level='warning',
        back_count=7
    )
    while True:
        try:
            s = Synchronizer()
            s.synchronize(**kwargs)
        except:
            logger.error(str(traceback.format_exc()))
        time.sleep(to_sleep)
