"""
Every user gets their own Redis hash to store "temporary" values in.
All values time out 24h after last update.
The hash is reset when the user logs out, or the user's id changes.
This is intended to persist some data between Dash callbacks.
If you use this for routes that take JWT authentication, there is no "logout" so the hash just expires after 24 hours.
"""

import os
from datetime import timedelta

from flask import g, has_app_context
from flask_login import current_user
from redis import Redis


def get_redis():
    r = getattr(g, '_redis', None) if has_app_context() else None
    if r is None:
        redis_host = os.environ.get('REDISSERVER', 'redis')
        redis_port = int(os.environ.get('REDISPORT', 6379))
        r = Redis(host=redis_host, port=redis_port, db=0)
        if has_app_context():
            g._redis = r
    return r


def set_value(key, value, hash_name=None):
    """
    :param key:
    :param value:
    :param hash_name:
    :return:
    """
    r = get_redis()
    if hash_name is None:
        hash_name = f'user{current_user.id}'
    if value is None:
        r.hdel(hash_name, key)
    else:
        r.hset(hash_name, key, value)
        r.expire(hash_name, timedelta(hours=24))


def get_value(key):
    """
    :param key:
    :return:
    """
    r = get_redis()
    hash_name = f'user{current_user.id}'
    return r.hget(hash_name, key)


def delete_value(key):
    """
    :param key:
    :return:
    """
    r = get_redis()
    hash_name = f'user{current_user.id}'
    return r.hdel(hash_name, key)


def clear_user_hash(user_id):
    r = get_redis()
    hash_name = f'user{user_id}'
    return r.delete(hash_name)


def exists(key):
    r = get_redis()
    hash_name = f'user{current_user.id}'
    return r.hexists(hash_name, key)
