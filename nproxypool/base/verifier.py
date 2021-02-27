# =============================================
# validation verification of a proxy
# ==============================================
import time
import asyncio
import aiohttp
import traceback
from lxml import etree
from abc import abstractmethod
from user_agent import generate_user_agent
from nproxypool.base.logger import get_logger
from nproxypool.base.db import RedisPool


class Base(object):
    def __init__(self):
        self._name = 'Default'
        self._url = 'https://feed.baidu.com/feed/api/tab/gettabinfo'
        self._time_out = 5
        self._max_worker = 20
        self._status_code_allowed = [200, 302, 303]
        self._loop = asyncio.new_event_loop()
        self._failure_list = []
        self._success_list = []
        self._logger = None
        self._os_type = {
            True: "android",
            False: ("mac", "win")
        }

    async def requests(self, method, url=None, is_mobile=False, **kwargs):
        kwargs.setdefault('timeout', aiohttp.ClientTimeout(self._time_out))
        if "headers" in kwargs:
            kwargs["headers"].setdefault("user-agent", generate_user_agent(os=self._os_type[is_mobile]))
        else:
            kwargs["headers"] = {
                "user-agent": generate_user_agent(os=self._os_type[is_mobile])
            }
        async with aiohttp.ClientSession() as session:
            async with session.request(method, url, **kwargs) as r:
                resp = r
                content_type = r.content_type
                if "text" in content_type or "html" in content_type:
                    content = await r.text(encoding=r.charset)
                    resp.xpath = etree.HTML(content).xpath
                elif "json" in content_type:
                    content = await r.json(encoding=r.charset)
                else:
                    content = await r.read()
                if r.status not in self._status_code_allowed:
                    self._logger.info('STATUS_CODE_NOT_ALLOWED ERROR')
                    raise Exception('!STATUS CODE ERROR!')
        return content, resp

    async def verify_worker(self, worker_name, queue):
        while True:
            proxy = await queue.get()
            _proxy = 'http://{}'.format(proxy) if not proxy.startswith('http') else proxy
            try:
                _start = time.monotonic()
                await self.requests('GET', self._url, proxy=_proxy)
                _time_consumed = round(time.monotonic() - _start, 2)
                self._logger.info(f'>>>{worker_name}-ip: {_proxy}, time_consumed: {_time_consumed}')
                self._success_list.append(proxy)
            except:
                self._failure_list.append(proxy)
                self._logger.info(f'!!!{worker_name}-ip: {_proxy}, FAILED')
            queue.task_done()

    async def verify(self, proxy_list):
        queue = asyncio.Queue()

        for _proxy in proxy_list:
            proxy = _proxy.decode()
            queue.put_nowait(proxy)

        tasks = []
        for i in range(self._max_worker):
            task = self._loop.create_task(self.verify_worker(f'{self._name}-{i}', queue))
            tasks.append(task)

        await queue.join()
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    @abstractmethod
    def init_verifier(self, **kwargs):
        pass

    @abstractmethod
    def run(self, **kwargs):
        pass


class Verifier(Base):
    def __init__(self):
        super(Verifier, self).__init__()
        self._redis_host = ''
        self._redis_port = ''
        self._password = ''
        self._from_db = 0
        self._from_db_key = ''
        self._is_from_db_zset = False
        self._to_db = 1
        self._to_db_key = ''
        self._is_to_db_zset = False
        self._score_threshold = 30
        self._score_decrease_by = 30
        self._redis_uri = "redis://:{password}@{host}:{port}/{db}"

    def init_verifier(self, **kwargs):
        """
        Initiate a verifier
        """
        self._redis_host = kwargs['host']
        self._redis_port = kwargs['port']
        self._password = kwargs['password']
        self._name = kwargs.get('name', 'Default')
        self._url = kwargs.get('url', 'https://feed.baidu.com/feed/api/tab/gettabinfo')
        self._max_worker = kwargs.get('max_worker', 20)
        self._time_out = kwargs.get('time_out', 5)
        self._from_db = kwargs.get('from_db', 0)
        self._from_db_key = kwargs.get('from_db_key', '')
        self._is_from_db_zset = kwargs.get('is_from_db_zset', False)
        self._to_db = kwargs.get('to_db', 1)
        self._to_db_key = kwargs.get('to_db_key', '')
        self._is_to_db_zset = kwargs.get('is_to_db_zset', False)
        self._score_threshold = kwargs.get('score_threshold', 30)
        self._score_decrease_by = kwargs.get('score_decrease_by', 30)

    def _delete_or_decrease(self, proxy: str, client: RedisPool, zset_key: str = ''):
        """
        Delete a proxy or decrease its score.
        """

        if not zset_key:
            value = client.get_one(proxy)
            if value:
                _, score = value.split(';')
                new_score = int(score) - self._score_decrease_by
                if new_score <= self._score_threshold:
                    client.delete_one(proxy)
                else:
                    client.update_one(
                        proxy,
                        new_score,
                        old_value=value
                    )
            else:
                client.z_decrease(
                    proxy,
                    zset_key,
                    score_threshold=self._score_threshold,
                    to_decr=self._score_decrease_by
                )

    def _insert_or_increase(self, proxy: str, client: RedisPool, zset_key: str = ''):
        """
        Insert a proxy or increase its score.
        """
        if not zset_key:
            value = client.get_one(proxy)
            if value:
                client.update_one(
                    proxy,
                    score=100,
                    old_value=value
                )
            else:
                client.insert_one(
                    proxy,
                    score=60
                )
        else:
            client.z_increase(
                proxy,
                zset_key
            )

    def _update(self, client: RedisPool, zset_key: str = ''):
        for proxy in self._failure_list:
            self._delete_or_decrease(
                proxy,
                client,
                zset_key=zset_key
            )
        for proxy in self._success_list:
            self._insert_or_increase(
                proxy,
                client,
                zset_key=zset_key
            )

    def _key_to_key_verify(self):
        """
        first-level pool to first-level pool update.
        """
        params = {
            'host': self._redis_host,
            'port': self._redis_port,
            'db': self._from_db,
            'password': self._password
        }
        client = RedisPool(**params)
        proxy_list = client.get_all()
        if proxy_list:
            self._loop.run_until_complete(self.verify(proxy_list))
            self._update(client)

    def _key_to_zset_verify(self):
        """
        first-level pool to second-level pool update.
        """
        params1 = {
            'host': self._redis_host,
            'port': self._redis_port,
            'db': self._from_db,
            'password': self._password
        }
        params2 = {
            'host': self._redis_host,
            'port': self._redis_port,
            'db': self._to_db,
            'password': self._password
        }
        client1 = RedisPool(**params1)
        client2 = RedisPool(**params2)
        proxy_list = client1.get_all()
        if proxy_list:
            self._loop.run_until_complete(self.verify(proxy_list))
            self._update(client2, zset_key=self._to_db_key)

    def _zest_to_zset_verify(self):
        """
        second-level pool to second-level pool update.
        """
        params = {
            'host': self._redis_host,
            'port': self._redis_port,
            'db': self._from_db,
            'password': self._password
        }
        client = RedisPool(**params)
        proxy_list = client.z_get_all(self._from_db_key)
        if proxy_list:
            self._loop.run_until_complete(self.verify(proxy_list))
            self._update(client, zset_key=self._to_db_key)

    def run(self, **kwargs):
        self.init_verifier(**kwargs)
        self._failure_list = []
        self._success_list = []
        if self._from_db == self._to_db and not self._is_from_db_zset:
            self._key_to_key_verify()
        elif self._is_to_db_zset and not self._is_from_db_zset:
            self._key_to_zset_verify()
        else:
            self._zest_to_zset_verify()


def run_verifier(**kwargs):
    time_sleep = kwargs.get('to_sleep', 10)
    _name = kwargs.get('name', 'Default')
    _name = 'verifier_{}'.format(_name)
    file_name = '{}.log'.format(_name)
    file_dir = kwargs.get('log_file_path')
    v_logger = get_logger(
        name=_name,
        filename=file_name,
        filedir=file_dir,
        level='warning',
        back_count=7
    )
    while True:
        try:
            v = Verifier()
            v._logger = v_logger
            v.run(**kwargs)
        except:
            v_logger.error(str(traceback.format_exc()))
        time.sleep(time_sleep)
