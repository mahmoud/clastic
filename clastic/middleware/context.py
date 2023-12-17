# -*- coding: utf-8 -*-

import sys
if sys.version_info < (3,3,):
    from collections import Mapping
else:
    from collections.abc import Mapping

from ..sinter import FunctionBuilder
from .core import Middleware

try:
    unicode
except NameError:
    # py3
    unicode = str


class ContextProcessor(Middleware):
    def __init__(self, required=None, defaults=None, overwrite=False):
        required = list(required or [])
        defaults = defaults or {}
        self._check_params(required, defaults, overwrite)

        self.required = required
        self.defaults = defaults
        self.overwrite = overwrite
        self.render = self._create_render()

    def __repr__(self):
        cn = self.__class__.__name__
        kwargs = []
        if self.required:
            kwargs.append('required=%r' % (self.required,))
        if self.defaults:
            kwargs.append('defaults=%r' % (self.defaults,))
        if self.overwrite:
            kwargs.append('overwrite=True')
        return '%s(%s)' % (cn, ', '.join(kwargs))

    def _check_params(self, required, defaults, overwrite):
        if not all([isinstance(arg, unicode) for arg in required]):
            raise TypeError('required argument names must be decoded strings')
        if not isinstance(defaults, Mapping):
            raise TypeError('defaults expected a dict (or mapping), not: %r'
                            % defaults)
        if not all([isinstance(arg, unicode) for arg in defaults.keys()]):
            raise TypeError('default argument names must be decoded strings')
        for reserved_arg in ('self', 'next', 'context'):
            if reserved_arg in defaults or reserved_arg in required:
                raise NameError('attempted to use reserved argument "%s"'
                                ' in ContextProcessor.' % reserved_arg)
        for arg in required:
            if arg in defaults:
                raise NameError('ambiguous argument %r appears in both '
                                'required and default argument lists.' % arg)

    def _create_render(self):
        def process_render_context(next, context, **kwargs):
            if not isinstance(context, Mapping):
                return next()
            desired_args = self.required + list(self.defaults.keys())
            for arg in desired_args:
                if not self.overwrite and arg in context:
                    continue
                context[arg] = kwargs.get(arg, self.defaults.get(arg))
            return next()

        def_items = self.defaults.items()
        _req_args = ['next', 'context'] + self.required + [arg for arg, val in def_items]
        _def_vals = [val for arg, val in def_items]

        fb = FunctionBuilder('process_render_context',
                             args=_req_args,
                             defaults=_def_vals)
        process_render_context._sinter_fb = fb

        return process_render_context


class SimpleContextProcessor(ContextProcessor):
    def __init__(self, *args, **kwargs):
        defaults = dict([(a, None) for a in args])
        defaults.update([(k.decode('utf8') if isinstance(k, bytes) else k, v)
                         for k, v in kwargs.items()])
        super(SimpleContextProcessor, self).__init__(defaults=defaults)
