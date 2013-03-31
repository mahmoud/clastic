from __future__ import unicode_literals

from clastic.core import Application
from clastic.render import default_response


def create_app(error_message, monitored_files=None):
    routes = [('/', get_message, default_response)]
    resources = {'error_message': error_message,
                 'monitored_files': monitored_files}
    app = Application(routes, resources)
    return app


def get_message(error_message, monitored_files):
    return ('whopps, looks like there might be an error: \n%s\n\n'
            '(monitoring files: %s)') % (error_message, monitored_files)
