# -*- coding: utf-8 -*-

from functools import wraps

from sinter import getargspec


def clastic_decorator(subdecorator):
    """
    If a decorator needs to accept *args and/or **kwargs,
    this function makes that possible by precomputing the
    argspec of the to-be-wrapped function and propagating
    it to the decorated version, where it is available to
    clastic for computing dependencies.
    """
    @wraps(subdecorator)
    def sinter_compatible_decorator(f):
        argspec = getargspec(f)
        if argspec.varargs or argspec.keywords:
            raise TypeError('clastic does not support functions with *args'
                            ' or **kwargs: %r' % f)
        ret = subdecorator(f)
        ret._argspec = argspec
        return ret
    return sinter_compatible_decorator
