from abc import abstractmethod
from nproxypool.base.db import RedisPool


class ProxyFetcherBase(object):
    def __init__(self, **kwargs):
        self._client = RedisPool(**kwargs)

    @abstractmethod
    def run(self):
        pass
