# -*- coding: utf-8 -*-

from collections import Mapping

from ..sinter import ArgSpec
from .core import Middleware


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
        if not all([isinstance(arg, basestring) for arg in required]):
            raise TypeError('required argument names must be strings')
        if not isinstance(defaults, Mapping):
            raise TypeError('defaults expected a dict (or mapping), not: %r'
                            % defaults)
        if not all([isinstance(arg, basestring) for arg in defaults.keys()]):
            raise TypeError('default argument names must be strings')
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
            desired_args = self.required + self.defaults.keys()
            for arg in desired_args:
                if not self.overwrite and arg in context:
                    continue
                context[arg] = kwargs.get(arg, self.defaults.get(arg))
            return next()

        _req_args = ['next', 'context'] + self.required + self.defaults.keys()
        _def_args = dict(self.defaults)
        process_render_context._argspec = ArgSpec(args=_req_args,
                                                  varargs=None,
                                                  keywords=None,
                                                  defaults=_def_args)
        return process_render_context


class SimpleContextProcessor(ContextProcessor):
    def __init__(self, *args, **kwargs):
        defaults = dict([(a, None) for a in args])
        defaults.update(kwargs)
        super(SimpleContextProcessor, self).__init__(defaults=defaults)
