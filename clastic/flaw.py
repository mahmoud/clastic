from __future__ import unicode_literals

import os
import re
from clastic.core import Application
from clastic.render import default_response


def create_app(error_message, monitored_files=None):
    routes = [('/', get_message, default_response)]
    non_site_files = _filter_site_files(monitored_files)
    parsed_tb = _ParsedTB.from_string(error_message)
    resources = {'error_message': error_message,
                 'parsed_error': parsed_tb,
                 'all_mon_files': monitored_files,
                 'mon_files': non_site_files}
    app = Application(routes, resources)
    return app


def get_message(error_message, parsed_error, mon_files):
    return ('whopps, looks like there might be an error (%s): \n%s\n\n'
            '(monitoring files: %s)') % (parsed_error.exc_type, error_message, mon_files)

#_FLAW_TEMPLATE = """\
#"""

_frame_re = re.compile(r'^File "(?P<filepath>.+)", line (?P<lineno>\d+),'
                       r' in (?P<funcname>.+)$')


class _ParsedTB(object):
    def __init__(self, exc_type_name, exc_msg, frames=None):
        self.exc_type = exc_type_name
        self.exc_msg = exc_msg
        self.frames = list(frames or [])

    @classmethod
    def from_string(cls, tb_str):
        if not isinstance(tb_str, unicode):
            tb_str = tb_str.decode('utf-8')
        tb_lines = tb_str.lstrip().splitlines()
        if not tb_lines[0].strip() == 'Traceback (most recent call last):':
            raise ValueError('unrecognized traceback string format')
        exc_str = tb_lines[-1]
        exc_type, _, exc_msg = exc_str.partition(':')
        frame_lines = tb_lines[1:-1]
        frames = []
        for pair_idx in range(0, len(frame_lines), 2):
            frame_line = frame_lines[pair_idx].strip()
            frame_dict = _frame_re.match(frame_line).groupdict()
            frame_dict['source_line'] = frame_lines[pair_idx + 1].strip()
            frames.append(frame_dict)

        return cls(exc_type, exc_msg, frames)



def _filter_site_files(paths):
    if not paths:
        return []
    site_dir = os.path.dirname(os.__file__)
    return [fn for fn in paths if not fn.startswith(site_dir)]
