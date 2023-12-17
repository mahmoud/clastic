# -*- coding: utf-8 -*-

import os

from pytest import raises

from clastic import Application
from clastic.render.chameleon_templates import ChameleonRenderFactory
from clastic.render import render_basic
from clastic.tests.common import hello_world_ctx, complex_context

_TMPL_DIR = os.path.join(os.path.dirname(__file__), '_chameleon_tmpls')


def test_chameleon():
    chameleon_render = ChameleonRenderFactory(_TMPL_DIR)
    tmpl = 'basic_template.pt'
    app = Application([('/', hello_world_ctx, tmpl),
                       ('/<name>/', hello_world_ctx, tmpl),
                       ('/beta/<name>/', complex_context, tmpl)],
                      render_factory=chameleon_render)

    c = app.get_local_client()
    resp = c.get('/')
    assert resp.status_code == 200
    assert b'clasty' in resp.data

    resp = c.get('/beta/Rajkumar/')
    assert resp.status_code == 200
    assert b'clasty' in resp.data


def test_chameleon_missing_template():
    chameleon_render = ChameleonRenderFactory(_TMPL_DIR)
    tmpl = 'missing_template.pt'
    with raises(ValueError):
        return Application([('/', hello_world_ctx, tmpl)],
                           render_factory=chameleon_render)


def test_chameleon_broken_template():
    chameleon_render = ChameleonRenderFactory(_TMPL_DIR)
    tmpl = 'broken_template_1.pt'
    app = Application([('/', hello_world_ctx, tmpl)],
                      render_factory=chameleon_render)
    c = app.get_local_client()
    resp = c.get('/')
    assert resp.status_code == 500
    assert len(resp.data) > 1024  # a longish response


def test_chameleon_mixed():
    chameleon_render = ChameleonRenderFactory(_TMPL_DIR)
    tmpl = 'basic_template.pt'
    app = Application([('/', hello_world_ctx, tmpl),
                       ('/json/', hello_world_ctx, render_basic)],
                      render_factory=chameleon_render)

    c = app.get_local_client()
    resp = c.get('/')
    assert resp.status_code == 200
    assert b'clasty' in resp.data

    resp = c.get('/json/')
    assert resp.status_code == 200
