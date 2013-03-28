from __future__ import unicode_literals

import os

from clastic.core import Application
from clastic.render import dev_json_response
from clastic.render import AshesRenderFactory

_CUR_DIR = os.path.dirname(__file__)

def create_app():
    routes = [('/', get_routes_info, dev_json_response),
              ('/beta/', get_routes_info, 'base.html')]
    arf = AshesRenderFactory(_CUR_DIR)
    app = Application(routes, {}, arf)
    return app


def get_routes_info(_application):
    ret = {}
    app = _application
    ret['routes'] = []
    for r in app.routes:
        ret['routes'].append(r.get_info())
    return ret

MetaApplication = create_app()

if __name__ == '__main__':
    MetaApplication.serve()
