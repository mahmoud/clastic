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

from clastic import (
    RESERVED_ARGS,
    Application,
    SubApplication,
    Route,
    Middleware,
    DummyMiddleware,
    Request,  # convenience
    Response
    )
