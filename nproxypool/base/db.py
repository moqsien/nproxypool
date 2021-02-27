# Redis Client to Save IPs
# -----------------------------------------
# every IP has an initial score as 60, decreases by 30 when a verification failure occurred,
# increase to 100 when a verification success occurred. An IP is removed when its score reach below 20.
#
# The score of an IP is decreased by 1 when fetched by a client.
# One ip is chosen among the highest scored ones when fetched by a client.
# -----------------------------------------
import time
from random import choice
from redis import ConnectionPool, StrictRedis
from nproxypool.utils.exceptions import PoolEmptyException


class RedisPoolBase(object):
    def __init__(self, **kwargs):
        self._kwargs = kwargs
        self._redis_uri = "redis://:{password}@{host}:{port}/{db}"
        self._client = None
        self._get_client()
        self._value_pattern = '{};{}'

    def __del__(self):
        if self._client:
            self._client.connection_pool.disconnect()

    def _get_client(self):
        if not self._kwargs.get('uri'):
            password = self._kwargs.get('password', '')
            host = self._kwargs.get('host', 'localhost')
            port = self._kwargs.get('port', '6379')
            db = self._kwargs.get('db', 1)
            redis_uri = self._redis_uri.format(
                password=password,
                host=host,
                port=port,
                db=db
            )
        else:
            redis_uri = self._kwargs['uri']
        pool = ConnectionPool.from_url(redis_uri)
        self._client = StrictRedis(connection_pool=pool)

    @staticmethod
    def _bytes_to_str(_value):
        res = _value
        if isinstance(_value, bytes):
            res = str(_value, encoding="utf-8")
        return res

    # ====================================
    #  first-level pool operations
    # ====================================
    def get_all(self):
        return self._client.keys()

    def get_one(self, key):
        """
        get one proxy from first-level pool
        key: proxy
        """
        r = self._client.get(key)
        return r if not r else self._bytes_to_str(r)

    def insert_one(self, key, score=60, expire=600):
        """
        insert one proxy to first-level pool
        key: proxy
        score: initial score
        expire: expire time
        """
        if not self.get_one(key):
            expire_stamp = int(time.time() + expire)
            value = self._value_pattern.format(expire_stamp, score)
            self._client.set(key, value)
            self._client.expireat(key, expire_stamp)

    def update_one(self, key, score=60, old_value=''):
        """
        update score but never change the expire time.
        """
        old_value = old_value or self.get_one(key)
        _expire = old_value.split(';')[0]
        expire_stamp = int(_expire) if _expire else int(time.time() - 300)
        new_value = self._value_pattern.format(expire_stamp, score)
        self._client.set(key, new_value)
        self._client.expireat(key, expire_stamp)

    def delete_one(self, key):
        self._client.delete(key)


class RedisPool(RedisPoolBase):
    def __init__(self, **kwargs):
        super(RedisPool, self).__init__(**kwargs)

    # ====================================
    #  second-level pool(zset) operations
    # ====================================
    def z_get_all_keys(self):
        return self._client.keys()

    def z_get_all(self, key):
        return self._client.zrangebyscore(key, -60, 100)

    def z_get(self, proxy, key):
        """
        query score or test whether the proxy is existed in a zset
        """
        return self._client.zscore(key, proxy)

    def z_add(self, proxy, key, score):
        if not self.z_get(proxy, key):
            _map = {proxy: score}
            self._client.zadd(key, _map)

    def z_increase(self, proxy, key):
        _map = {proxy: 100}
        self._client.zadd(key, _map)

    def z_delete(self, proxy, key):
        self._client.zrem(key, proxy)

    def z_decrease(self, proxy, key, score_threshold=20, to_decr=30):
        """
        score_threshold: threshold for proxy delete
        to_decr: score to decrease by when a verification failure occurred
        """
        score = self.z_get(proxy, key)
        if score:
            new_score = score - to_decr
            if new_score <= score_threshold:
                self.z_delete(proxy, key)
            else:
                self._client.zincrby(
                    name=key,
                    value=proxy,
                    amount=0 - to_decr
                )

    def z_random_get_one(self, key='baidu'):
        res = self._client.zrangebyscore(key, 100, 100)
        if not res:
            res = self._client.zrangebyscore(key, 85, 100)
        if res:
            proxy = choice(res)
            proxy = self._bytes_to_str(proxy)
            self.z_decrease(proxy, key, to_decr=1)
            return proxy
        else:
            raise PoolEmptyException()

    def z_get_total_num(self, key, min_score=0, max_score=100, get_list=False):
        res = self._client.zrangebyscore(key, min_score, max_score)
        if not get_list:
            return len(res)
        else:
            return [self._bytes_to_str(i) for i in res]
