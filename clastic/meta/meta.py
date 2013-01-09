from __future__ import unicode_literals

from clastic.core import Application
from clastic.render import dev_json_response


def create_app():
    app = Application([('/', get_routes_info, dev_json_response)])
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
