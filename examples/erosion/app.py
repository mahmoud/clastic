# -*- coding: utf-8 -*-

import os
import sys
import json
import string
import codecs
from collections import OrderedDict

_CUR_PATH = os.path.dirname(os.path.abspath(__file__))
_CLASTIC_PATH = os.path.dirname(os.path.dirname(_CUR_PATH))
sys.path.append(_CLASTIC_PATH)

try:
    import clastic
except ImportError:
    print "make sure you've got werkzeug and other dependencies installed"

from clastic import Application, POST, redirect
from clastic.errors import Forbidden
from clastic.render import AshesRenderFactory

# TODO: yell if static hosting is the same location as the application assets

_DEFAULT_LINKS_FILE_PATH = os.path.join(_CUR_PATH, 'links.txt')


_CHAR_LIST = string.ascii_lowercase + string.digits
_CHAR_LIST = sorted(set(_CHAR_LIST) - set('l'))
_CHAR_IDX_MAP = dict((c, i) for i, c in enumerate(_CHAR_LIST))
_CHARSET_LEN = len(_CHAR_LIST)


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


def home():
    return {}


def add_entry(target, alias=None, expiry=None, clicks=None):
    if target.startswith('/'):
        # check accessibility/existence of file?
        pass
    pass


def fetch_entry(link_map, link_alias, request, local_static_app=None):
    try:
        target = link_map.get_entry(link_alias)
    except KeyError:
        return Forbidden()  # 404? 402?
    if target.startswith('/'):
        if local_static_app:
            return local_static_app.get_file_response(target, request)
        else:
            return Forbidden()
    else:
        return redirect(target, code=307)


def get_link_list(link_list_path=None):
    if link_list_path is None:
        link_list_path = os.path.join(_CUR_PATH, 'link_list.csv')
    pass


def create_app(link_list_path=None, local_root=None):
    link_list_path = link_list_path or _DEFAULT_LINKS_FILE_PATH
    link_map = LinkMap(link_list_path)
    resources = {'link_map': link_map}
    routes = [('/', home, 'home.html')]
              #POST('/submit', add_entry)]
    arf = AshesRenderFactory(_CUR_PATH)
    app = Application(routes, resources, arf)
    return app


def main():
    app = create_app()
    app.serve()


class LinkEntry(object):
    def __init__(self, alias, target, expiry=None, max_count=None, count=0):
        self.alias = alias
        self.target = target
        self.max_count = max_count
        self.expire_time = expiry
        self.count = count

    @classmethod
    def from_dict(cls, **kwargs):
        return cls(**kwargs)

    def to_dict(self):
        return dict(self.__dict__)


class LinkMap(object):
    def __init__(self, path):
        self.path = path
        entries = _load_entries_from_file(path)
        self.link_map = OrderedDict(entries)

    def add_link(self, alias, target, expiry=None, max_count=None):
        if alias in self.link_map:
            raise ValueError('alias already in use %r' % alias)
        self.link_map[alias] = LinkEntry(alias, target, expiry, max_count)

    def get_target(self, alias):
        return self.link_map[alias]

    def save(self):
        # TODO: high-water mark appending
        with open(self.path, 'w') as f:
            for alias, entry in self.link_map.iteritems():
                entry_json = json.dumps(entry.to_dict())
                f.write(entry_json)
                f.write('\n')
        # sync


def _load_entries_from_file(path):
    ret = []
    if not os.path.exists(path):
        return ret
    with codecs.open(path, 'r', 'utf-8') as f:
        for line in f:
            entry_dict = json.loads(line)
            ret.append(LinkEntry.from_dict(entry_dict))
    return ret


if __name__ == '__main__':
    main()
