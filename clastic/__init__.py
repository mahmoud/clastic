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

from core import (
    RESERVED_ARGS,
    Application,
    SubApplication,
    Route
    )

from middleware import Middleware, DummyMiddleware, GetParamMiddleware
from render import json_response, default_response
from meta import MetaApplication

from werkzeug.wrappers import Request, Response
