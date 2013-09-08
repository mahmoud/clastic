# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from nose.tools import eq_, raises

import json

from werkzeug.test import Client
from werkzeug.wrappers import BaseResponse

from clastic import Application, render_json, render_basic
from clastic.middleware import SimpleContextProcessor, ContextProcessor
from common import (hello_world,
                    hello_world_str,
                    hello_world_ctx,
                    RequestProvidesName)


def test_simple_ctx_proc():
    add_name_lang = SimpleContextProcessor(name='Kurt', language='en')
    app = Application([('/', hello_world_ctx, render_json)],
                      middlewares=[add_name_lang])
    c = Client(app, BaseResponse)
    resp = c.get('/')
    resp_data = json.loads(resp.data)
    yield eq_, resp_data['name'], 'world'  # does not overwrite
    yield eq_, resp_data['language'], 'en'


def test_ctx_proc_req():
    req_provides_name = RequestProvidesName()
    add_name_lang = ContextProcessor(['name'], {'language': 'en'})
    app = Application([('/', hello_world_ctx, render_json)],
                      middlewares=[req_provides_name, add_name_lang])
    c = Client(app, BaseResponse)
    resp = c.get('/')
    resp_data = json.loads(resp.data)
    yield eq_, resp_data['name'], 'world'  # does not overwrite
    yield eq_, resp_data['language'], 'en'

    resp = c.get('/?name=Alex')
    resp_data = json.loads(resp.data)
    yield eq_, resp_data['name'], 'Alex'  # still does not overwrite


def test_ctx_proc_overwrite():
    add_name = ContextProcessor(defaults={'name': 'Kurt'}, overwrite=True)
    app = Application([('/', hello_world_ctx, render_json)],
                      middlewares=[add_name])
    c = Client(app, BaseResponse)
    resp = c.get('/')
    resp_data = json.loads(resp.data)
    yield eq_, resp_data['name'], 'Kurt'  # does overwrite


def test_ctx_proc_empty():
    add_name = ContextProcessor()
    app = Application([('/', hello_world_ctx, render_json)],
                      middlewares=[add_name])
    c = Client(app, BaseResponse)
    resp = c.get('/')
    resp_data = json.loads(resp.data)
    yield eq_, resp_data['name'], 'world'  # does overwrite


def test_ctx_proc_direct_resp():
    add_name = ContextProcessor(defaults={'name': 'Kurt'})
    app = Application([('/', hello_world)],
                      middlewares=[add_name])
    c = Client(app, BaseResponse)
    resp = c.get('/')
    yield eq_, resp.data, 'Hello, world!'


def test_ctx_proc_nonctx():
    add_name = ContextProcessor(defaults={'name': 'Kurt'})
    app = Application([('/', hello_world_str, render_basic)],
                      middlewares=[add_name])
    c = Client(app, BaseResponse)
    resp = c.get('/')
    yield eq_, resp.data, 'Hello, world!'


@raises(NameError)
def test_ctx_proc_unresolved():
    add_name = ContextProcessor(['name'])
    Application([('/', hello_world)],
                middlewares=[add_name])


@raises(NameError)
def test_ctx_proc_overlap():
    ContextProcessor(required=['name'],
                     defaults={'name': 'Alex'})


@raises(NameError)
def test_ctx_proc_reserved():
    ContextProcessor(required=['next'])


@raises(TypeError)
def test_ctx_proc_req_type():
    ContextProcessor(required=[6])


@raises(TypeError)
def test_ctx_proc_default_type():
    ContextProcessor(default={6: ''})


@raises(TypeError)
def test_ctx_proc_def_nonmap():
    ContextProcessor(defaults=['hi', 'hello'])
