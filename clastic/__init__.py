#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    clastic
    ~~~~~~~

    A functional Python web framework that streamlines explicit
    development practices while eliminating global state.

    :copyright: (c) 2012 by Mahmoud Hashemi
    :license: BSD, see LICENSE for more details.

"""
import server

from core import (RESERVED_ARGS,
                  Application,
                  SubApplication,
                  Route)

from middleware import Middleware, GetParamMiddleware
from render import render_json, render_json_dev, render_basic
from meta import MetaApplication
from static import StaticApplication

from werkzeug.wrappers import Request, Response
from werkzeug.utils import redirect, append_slash_redirect


# TODO: deprecate
from render import json_response, default_response
