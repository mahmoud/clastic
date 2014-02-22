# -*- coding: utf-8 -*-

import sys
sys.path.append('..')  # to work out of the box in the source tree

import json
import urllib2

from clastic import Application
from clastic.render import render_basic
from clastic.middleware import GetParamMiddleware

_DEFAULT_URL = ('https://en.wikipedia.org/w/api.php?action=query&titles='
                'Clastic|Geology|Tea&prop=info&inprop=protection&format=json')


def fetch_json(url):
    url = url or _DEFAULT_URL
    response = urllib2.urlopen(url)
    content = response.read()
    data = json.loads(content)
    return data


def create_app():
    routes = [('/', fetch_json, render_basic)]
    mws = [GetParamMiddleware('url')]
    app = Application(routes, middlewares=mws)
    return app


wsgi_app = create_app()


if __name__ == '__main__':
    wsgi_app.serve()
