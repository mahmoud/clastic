# -*- coding: utf-8 -*-
"""
Cline is a microframework that replicates bottle.py's interface, but
built with Clastic primitives, enabling better state management and
stronger type/argument checking.

Etymologically, A cline is a continuum or threshold (related to
"incline"/"decline"), and is often referenced in geological
discussions of layering. In historical terms, flask seems to have
spawned bottle, which spawned klein (Twisted's bottle-alike), from
which Cline partially derives its name.
"""

from route import HTTP_METHODS
from application import Application


def run(app=None,
        server='wsgiref',
        host='0.0.0.0',
        port=5000,
        interval=1,
        reloader=False,
        quiet=False,
        plugins=None,
        debug=None,
        **kwargs):
    "TODO: prioritize clastic or bottle API similarity?"
    if app is None:
        app = DEFAULT_APP
    # TODO


class Cline(Application):
    def __init__(self, catchall=True, autojson=True):
        pass

    def route(self, path, method='GET', callback=None, **kwargs):
        pass

    for http_method in HTTP_METHODS:
        pass


DEFAULT_APP = Cline()
route = DEFAULT_APP.route
for http_method in HTTP_METHODS:
    pass  # TODO: convenience decorators
