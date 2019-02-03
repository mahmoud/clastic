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

from .route import Route
from .application import Application
from .render import render_basic


class Cline(Application):
    def __init__(self, **kw):
        self.autorender = kw.pop('autorender', True)
        super(Cline, self).__init__(**kw)

    def run(self, address='0.0.0.0', port=5000,  **kw):
        return self.serve(address=address, port=port, **kw)

    def route(self, path, methods=None, endpoint_func=None, **kwargs):
        def create_and_add_route(endpoint_func):
            _route = Route(path, endpoint_func, **kwargs)
            self.add(_route)
            return endpoint_func

        if self.autorender and not kwargs.get('render'):
            kwargs['render'] = render_basic
        kwargs['methods'] = methods

        if endpoint_func is None:
            return create_and_add_route
        elif not callable(endpoint_func):
            fn = self.__class__.__name__ + '.route()'
            raise TypeError('%s expects a callable endpoint function' % fn)
        else:
            return create_and_add_route(endpoint_func)

    def get(self, path, endpoint=None, **kwargs):
        return self.route(path, ('GET',), endpoint, **kwargs)

    def post(self, path, endpoint=None, **kwargs):
        return self.route(path, ('POST',), endpoint, **kwargs)

    def put(self, path, endpoint=None, **kwargs):
        return self.route(path, ('PUT',), endpoint, **kwargs)

    def delete(self, path, endpoint=None, **kwargs):
        return self.route(path, ('DELETE',), endpoint, **kwargs)

    def patch(self, path, endpoint=None, **kwargs):
        return self.route(path, ('PATCH',), endpoint, **kwargs)

    def head(self, path, endpoint=None, **kwargs):
        return self.route(path, ('HEAD',), endpoint, **kwargs)


DEFAULT_APP = Cline()
for attr in ('run', 'route', 'get', 'post', 'put', 'delete', 'patch', 'head'):
    globals()[attr] = getattr(DEFAULT_APP, attr)
