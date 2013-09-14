# -*- coding: utf-8 -*-

import os
import sys
import json
from collections import OrderedDict

_CUR_PATH = os.path.dirname(os.path.abspath(__file__))
_CLASTIC_PATH = os.path.dirname(os.path.dirname(_CUR_PATH))
sys.path.append(_CLASTIC_PATH)

try:
    import clastic
except ImportError:
    print "make sure you've got werkzeug and other dependencies installed"

from clastic import Application
from clastic.render import render_json, AshesRenderFactory


def home():
    return {}


def add_entry(target, name=None, expiry=None, clicks=None):
    pass


def fetch_entry(link_map, link_alias):
    try:
        target = link_map.get_entry(link_alias)
    except KeyError:
        raise  # 404? 403? 402?
    if target.startswith('/'):
        pass  # delegate to static application
    else:
        pass  # use temporary redirect
    pass


def get_link_list(link_list_path=None):
    if link_list_path is None:
        link_list_path = os.path.join(_CUR_PATH, 'link_list.csv')
    pass


def create_app(link_list_path=None, local_root=None):
    link_list_path = link_list_path or os.path.join(_CUR_PATH, 'links.txt')
    link_map = LinkMap(link_list_path)
    resources = {'link_map': link_map}
    routes = [('/', home, 'home.html'),
              ('/submit', add_entry),
              ('/list', get_link_list, 'list.html')]
    arf = AshesRenderFactory(_CUR_PATH)
    app = Application(routes, resources, arf)
    return app


def main():
    app = create_app()
    app.serve()


class LinkMap(object):
    def __init__(self, path):
        self.path = path
        entries = _load_entries_from_file(path)
        self.link_map = OrderedDict(entries)

    def add_link(self, alias, target):
        if alias in self.link_map:
            raise ValueError('alias already in use %r' % alias)
        self.link_map[alias] = target

    def get_target(self, alias):
        return self.link_map[alias]

    def save(self):
        # TODO: high-water mark appending
        with open(self.path, 'w') as f:
            for alias, target in self.link_map.iteritems():
                entry = json.dumps({'alias': alias, 'target': target})
                f.write(entry)
                f.write('\n')
        # sync


if __name__ == '__main__':
    main()
