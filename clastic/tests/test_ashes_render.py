# -*- coding: utf-8 -*-

import os
from pytest import raises

from clastic import Application
from clastic.render import ashes
from clastic.render import AshesRenderFactory, render_basic
from clastic.tests.common import hello_world_ctx, complex_context

_TMPL_DIR = os.path.join(os.path.dirname(__file__), '_ashes_tmpls')


def test_ashes():
    ashes_render = AshesRenderFactory(_TMPL_DIR)
    tmpl = 'basic_template.html'
    app = Application([('/', hello_world_ctx, tmpl),
                       ('/<name>/', hello_world_ctx, tmpl),
                       ('/beta/<name>/', complex_context, tmpl)],
                      render_factory=ashes_render)

    c = app.get_local_client()
    resp = c.get('/')
    assert resp.status_code == 200
    assert b'world' in resp.data

    resp = c.get('/beta/Rajkumar/')
    assert resp.status_code, 200
    assert b'Rajkumar' in resp.data

    # test rebind

    # no loss of binding on applications with no render factory
    wrap_app = Application([('/', app)])
    assert wrap_app.routes[0].render_factory is ashes_render
    c = wrap_app.get_local_client()
    resp = c.get('/')
    assert resp.status_code == 200
    assert b'<html>' in resp.data
    assert b'world' in resp.data

    # test bind new but not old
    ashes_render2 = AshesRenderFactory(_TMPL_DIR)
    wrap_app2 = Application([('/test', hello_world_ctx, tmpl),
                             ('/', app)], render_factory=ashes_render2)
    assert wrap_app2.routes[0].render_factory is ashes_render2
    assert wrap_app2.routes[1].render_factory is ashes_render


def test_ashes_missing_template():
    ashes_render = AshesRenderFactory(_TMPL_DIR)
    tmpl = 'missing_template.html'
    with raises(ashes.TemplateNotFound):
        return Application([('/', hello_world_ctx, tmpl)],
                           render_factory=ashes_render)
    return


def test_ashes_mixed():
    ashes_render = AshesRenderFactory(_TMPL_DIR)
    tmpl = 'basic_template.html'
    app = Application([('/', hello_world_ctx, tmpl),
                       ('/json/', hello_world_ctx, render_basic)],
                      render_factory=ashes_render)

    c = app.get_local_client()
    resp = c.get('/')
    assert resp.status_code == 200
    assert b'Salam' in resp.data

    resp = c.get('/json/')
    assert resp.status_code == 200
