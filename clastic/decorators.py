# -*- coding: utf-8 -*-

from functools import wraps

from .sinter import get_fb


def clastic_decorator(subdecorator):
    """
    If a decorator needs to accept *args and/or **kwargs,
    this function makes that possible by precomputing the
    signature of the to-be-wrapped function and propagating
    it to the decorated version, where it is available to
    clastic for computing dependencies.
    """
    @wraps(subdecorator)
    def sinter_compatible_decorator(f):
        fb = get_fb(f)

        if fb.varargs or fb.varkw:
            raise TypeError('clastic does not support functions with *args'
                            ' or **kwargs: %r' % f)
        ret = subdecorator(f)
        ret._sinter_fb = fb
        return ret
    return sinter_compatible_decorator
