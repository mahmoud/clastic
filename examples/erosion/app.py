# -*- coding: utf-8 -*-

import os
import sys
import json
import time
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
from clastic.utils import Redirector
from clastic.errors import Forbidden
from clastic.render import AshesRenderFactory
from clastic.middleware import SimpleContextProcessor
from clastic.middleware.form import PostDataMiddleware

# TODO: yell if static hosting is the same location as the application assets

_DEFAULT_LINKS_FILE_PATH = os.path.join(_CUR_PATH, 'links.txt')


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


def add_entry(link_map, target_url, target_file, alias,
              expiry_time, max_count):
    target = target_url or target_file
    if not target:
        raise ValueError('expected one of target url or file')
    entry = link_map.add_entry(target, alias, expiry_time, max_count)
    return {'entry': entry}


def add_entry_render(context, link_map):
    print 'yay', context
    link_map.save()
    return redirect('/', code=303)


def get_entry(link_map, alias, request, local_static_app=None):
    try:
        entry = link_map.get_entry(alias)
    except KeyError:
        return Forbidden()  # 404? 402?
    target_location = entry.target
    if target_location.startswith('/'):
        if local_static_app:
            return local_static_app.get_file_response(target, request)
        return Forbidden()
    else:
        return redirect('http://' + target_location, code=301)


def create_app(link_list_path=None, local_root=None):
    link_list_path = link_list_path or _DEFAULT_LINKS_FILE_PATH
    link_map = LinkMap(link_list_path)
    resources = {'link_map': link_map, 'local_root': local_root}

    pdm = PostDataMiddleware({'target_url': unicode,
                              'target_file': unicode,
                              'alias': unicode,
                              'max_count': int,
                              'expiry_time': unicode})
    submit_route = POST('/submit', add_entry, add_entry_render)
    submit_route._middlewares.append(pdm)

    routes = [('/', home, 'home.html'),
              submit_route,
              ('/<path:alias>', get_entry)]
    scp = SimpleContextProcessor('local_root')
    arf = AshesRenderFactory(_CUR_PATH, keep_whitespace=False)
    app = Application(routes, resources, arf, [scp])
    return app


def make_redirector(location='/', code=301):
    def _redirect():
        return redirect(location, code=code)
    return _redirect


def main():
    app = create_app(local_root='/tmp/')
    #app = create_app()
    app.serve(use_lint=False)


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


class LinkMap(object):
    def __init__(self, path):
        self.path = path
        entries = _load_entries_from_file(path)
        self.link_map = OrderedDict([(e.alias, e) for e in entries])

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

    def get_entry(self, alias):
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
