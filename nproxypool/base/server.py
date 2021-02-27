import os
import traceback
from flask import Flask, request
from flask_restful import Api, Resource
from nproxypool.base.db import RedisPool
from nproxypool.utils.exceptions import PoolEmptyException
from nproxypool.utils.misc import get_sychronizer_config, get_redis_config


POOL = None


def get_second_level_pool(dir):
    synch_config = get_sychronizer_config(dir)
    redis_config = get_redis_config(dir)
    redis_config['db'] = synch_config['second_db']
    global POOL
    POOL = RedisPool(**redis_config)


class GetProxyRandomly(Resource):
    """
    'key' is a key in second-level pool 
    """
    @staticmethod
    def get():
        key = request.args.get('key')
        try:
            if key:
                proxy = POOL.z_random_get_one(key=key)
                res = {
                    'proxy': proxy
                }
            else:
                res = {
                    'errMsg': 'please input a key'
                }
        except PoolEmptyException:
            res = {
                'errMsg': 'proxy pool is empty: {}'.format(str(traceback.format_exc()))
            }
        except:
            res = {
                'errMsg': 'query error{}'.format(str(traceback.format_exc()))
            }
        return res


class GetProxyTotalNum(Resource):
    @staticmethod
    def get():
        _key = request.args.get('key')
        _min = int(request.args.get('min', '0'))
        _max = int(request.args.get('max', '100'))
        _min = 0 if (_min < 0 or _min > 100) else _min
        _max = 100 if (_max < _min or _max > 100) else _max
        res = {}
        if bytes(_key, encoding='utf-8') in POOL.z_get_all_keys():
            _total = POOL.z_get_total_num(_key, min_score=_min, max_score=_max)
            res[_key] = _total
        else:
            res['errMsg'] = 'invalid key: {}'.format(_key)
        return res


class GetProxyList(Resource):
    @staticmethod
    def get():
        _key = request.args.get('key')
        _min = int(request.args.get('min', '0'))
        _max = int(request.args.get('max', '100'))
        _min = 0 if (_min < 0 or _min > 100) else _min
        _max = 100 if (_max < _min or _max > 100) else _max
        res = {}
        if bytes(_key, encoding='utf-8') not in POOL.z_get_all_keys():
            res['errMsg'] = 'invalid key: {}'.format(_key)
        else:
            _list = POOL.z_get_total_num(_key, min_score=_min, max_score=_max, get_list=True)
            res[_key] = {
                'total': len(_list),
                'list': _list
            }
        return res


def make_app(dir):
    get_second_level_pool(dir)
    app = Flask(__name__)
    api = Api(app=app)
    api.add_resource(GetProxyRandomly, '/proxy/random/')
    api.add_resource(GetProxyTotalNum, '/proxy/total/')
    api.add_resource(GetProxyList, '/proxy/list/')
    return app
