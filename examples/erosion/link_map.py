# -*- coding: utf-8 -*-

import os
import json
import time
import codecs
import string
from collections import OrderedDict
from threading import RLock


_CHAR_LIST = string.ascii_lowercase + string.digits
_CHAR_LIST = sorted(set(_CHAR_LIST) - set('l'))
_CHAR_IDX_MAP = dict((c, i) for i, c in enumerate(_CHAR_LIST))
_CHARSET_LEN = len(_CHAR_LIST)


_NEVER = object()
_EXPIRY_MAP = {'mins': 5 * 60,
               'hour': 1 * 60 * 60,
               'day': 24 * 60 * 60,
               'month': 30 * 24 * 60 * 60,
               'never': _NEVER}
_DEFAULT_EXPIRY = 'hour'


class _synchronized(object):

    def __init__(self, lock, func):
        self.lock = lock
        self.func = func

    def __call__(self, *args, **kwargs):
        with self.lock:
            return self.func(*args, **kwargs)

    def __get__(self, obj, type_=None):
        if obj is None:
            return self
        return self.__class__(self.lock,
                              self.func.__get__(obj, type))


def synchronized(lock):
    return lambda func: _synchronized(lock, func)


def id_decode(text):
    ret = 0
    for i, c in enumerate(text[::-1]):
        ret += _CHARSET_LEN ** i * _CHAR_IDX_MAP[c]
    return ret


def id_encode(id_int):
    ret = ''
    id_int = abs(id_int)
    while id_int:
        ret = _CHAR_LIST[id_int % _CHARSET_LEN] + ret
        id_int /= _CHARSET_LEN
    return ret or _CHAR_LIST[0]


class LinkEntry(object):
    def __init__(self, link_id, target, alias,
                 expiry_time=None, max_count=None, count=0):
        self.link_id = link_id
        self.alias = alias
        self.target = target
        self.max_count = max_count
        self.expiry_time = expiry_time
        self.count = count

    @classmethod
    def from_dict(cls, in_dict):
        return cls(**in_dict)

    def to_dict(self):
        return dict(self.__dict__)

    def __repr__(self):
        cn = self.__class__.__name__
        kwargs = self.__dict__
        return ('{cn}({link_id}, {target!r}, {alias!r}, '
                '{expiry_time}, {max_count}, {count})'.format(cn=cn, **kwargs))

LOCK = RLock()

class LinkMap(object):
    def __init__(self, path):
        self.path = path
        entries = _load_entries_from_file(path)
        self.link_map = OrderedDict([(e.alias, e) for e in entries])

    @synchronized(LOCK)
    def add_entry(self, target, alias=None, expiry=None, max_count=None):
        next_id = self._get_next_id()
        if not alias:
            alias = id_encode(next_id)
        if alias in self.link_map:
            raise ValueError('alias already in use %r' % alias)
        expire_time = self._get_expiry_time(expiry)

        entry = LinkEntry(next_id, target, alias, expire_time, max_count)
        self.link_map[entry.alias] = entry
        return entry

    def _get_expiry_time(self, expire_interval_name):
        expire_interval_name = expire_interval_name or _DEFAULT_EXPIRY
        expiry_seconds = _EXPIRY_MAP[expire_interval_name]
        if expiry_seconds is _NEVER:
            expiry_time = None
        else:
            cur_time = time.time()
            expiry_time = int(cur_time + expiry_seconds)
        return expiry_time

    def _get_next_id(self):
        try:
            last_alias = next(reversed(self.link_map))
            last_id = self.link_map[last_alias].link_id
        except:
            last_id = 41660
        return last_id + 1

    @synchronized(LOCK)
    def get_entry(self, alias, enforce=True):
        ret = self.link_map[alias]
        if enforce:
            if ret.max_count <= ret.count or ret.expiry_time < time.time():
                raise ValueError()
        return ret

    @synchronized(LOCK)
    def use_entry(self, alias):
        try:
            ret = self.get_entry(alias)
        except:
            return None
        ret.count += 1
        return ret

    @synchronized(LOCK)
    def save(self):
        # TODO: high-water mark appending
        with open(self.path, 'w') as f:
            for alias, entry in self.link_map.iteritems():
                entry_json = json.dumps(entry.to_dict())
                f.write(entry_json)
                f.write('\n')
        # sync


@synchronized(LOCK)
def _load_entries_from_file(path):
    ret = []
    if not os.path.exists(path):
        return ret
    with codecs.open(path, 'r', 'utf-8') as f:
        for line in f:
            entry_dict = json.loads(line)
            ret.append(LinkEntry.from_dict(entry_dict))
    return ret
