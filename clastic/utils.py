# -*- coding: utf-8 -*-

from werkzeug.utils import redirect


class Redirector(object):
    """
    Meant to be used as a render step after a POST.

    partial() meets render().
    """
    def __init__(self, location, code=301):
        # TODO: make location a lamda
        self.location = location
        self.code = code

    def __call__(self):
        return redirect(self.location, code=self.code)

    def __repr__(self):
        cn = self.__class__.__name__
        return '%s(%r, code=%r)' % (cn, self.location, self.code)
