# -*- coding: utf-8 -*-

import os
import sys

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


def fetch_entry(link_alias):
    pass


def get_link_list(link_list_path=None):
    if link_list_path is None:
        link_list_path = os.path.join(_CUR_PATH, 'link_list.csv')
    pass


def create_app(local_root=None):
    routes = [('/', home, 'home.html'),
              ('/submit', add_entry),
              ('/list', get_link_list, 'list.html')]
    arf = AshesRenderFactory(_CUR_PATH)
    app = Application(routes, {}, arf)
    return app


if __name__ == '__main__':
    app = create_app()
    app.serve()
