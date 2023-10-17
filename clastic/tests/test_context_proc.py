# -*- coding: utf-8 -*-

from pytest import raises

import json

from clastic import Application, render_json, render_basic
from clastic.middleware import SimpleContextProcessor, ContextProcessor
from clastic.tests.common import (hello_world,
                                  hello_world_str,
                                  hello_world_ctx,
                                  RequestProvidesName)


def test_simple_ctx_proc():
    add_name_lang = SimpleContextProcessor(name='Kurt', language='en')
    app = Application([('/', hello_world_ctx, render_json)],
                      middlewares=[add_name_lang])
    c = app.get_local_client()
    resp = c.get('/')
    resp_data = json.loads(resp.get_data(True))
    assert resp_data['name'] == 'world'  # does not overwrite
    assert resp_data['language'] == 'en'


def test_ctx_proc_req():
    req_provides_name = RequestProvidesName()
    add_name_lang = ContextProcessor(['name'], {'language': 'en'})
    app = Application([('/', hello_world_ctx, render_json)],
                      middlewares=[req_provides_name, add_name_lang])
    c = app.get_local_client()
    resp = c.get('/')
    resp_data = json.loads(resp.get_data(True))
    assert resp_data['name'] == 'world'  # does not overwrite
    assert resp_data['language'] == 'en'

    resp = c.get('/?name=Alex')
    resp_data = json.loads(resp.get_data(True))
    assert resp_data['name'] == 'Alex'  # still does not overwrite


def test_ctx_proc_overwrite():
    add_name = ContextProcessor(defaults={'name': 'Kurt'}, overwrite=True)
    app = Application([('/', hello_world_ctx, render_json)],
                      middlewares=[add_name])
    c = app.get_local_client()
    resp = c.get('/')
    resp_data = json.loads(resp.get_data(True))
    assert resp_data['name'] == 'Kurt'  # does overwrite


def test_ctx_proc_empty():
    add_name = ContextProcessor()
    app = Application([('/', hello_world_ctx, render_json)],
                      middlewares=[add_name])
    c = app.get_local_client()
    resp = c.get('/')
    resp_data = json.loads(resp.get_data(True))
    assert resp_data['name'] == 'world'  # does overwrite


def test_ctx_proc_direct_resp():
    add_name = ContextProcessor(defaults={'name': 'Kurt'})
    app = Application([('/', hello_world)],
                      middlewares=[add_name])
    c = app.get_local_client()
    resp = c.get('/')
    assert resp.data == b'Hello, world!'


def test_ctx_proc_nonctx():
    add_name = ContextProcessor(defaults={'name': 'Kurt'})
    app = Application([('/', hello_world_str, render_basic)],
                      middlewares=[add_name])
    c = app.get_local_client()
    resp = c.get('/')
    assert resp.data == b'Hello, world!'


def test_ctx_proc_unresolved():
    with raises(NameError):
        add_name = ContextProcessor(['name'])
        Application([('/', hello_world)],
                    middlewares=[add_name])


def test_ctx_proc_overlap():
    with raises(NameError):
        ContextProcessor(required=['name'],
                         defaults={'name': 'Alex'})


def test_ctx_proc_reserved():
    with raises(NameError):
        ContextProcessor(required=['next'])


def test_ctx_proc_req_type():
    with raises(TypeError):
        ContextProcessor(required=[6])


def test_ctx_proc_default_type():
    with raises(TypeError):
        ContextProcessor(defaults={6: ''})


def test_ctx_proc_def_nonmap():
    with raises(TypeError):
        ContextProcessor(defaults=['hi', 'hello'])
