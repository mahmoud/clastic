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



example = """
Traceback (most recent call last):
  File "example.py", line 34, in <module>
      create_decked_out_app().serve()
  File "/home/mahmoud/projects/clastic/clastic/core.py", line 147, in serve
      run_simple(address, port, wrapped_wsgi, **kw)
  File "/home/mahmoud/projects/clastic/clastic/server.py", line 134, in run_simple
      run_with_reloader(serve_forever, extra_files, reloader_interval)
  File "/home/mahmoud/projects/clastic/clastic/server.py", line 107, in run_with_reloader
      sys.exit(restart_with_reloader())
  File "/home/mahmoud/projects/clastic/clastic/server.py", line 75, in restart_with_reloader
      err_app = flaw.create_app(stderr_data, to_mon)
  File "/home/mahmoud/projects/clastic/clastic/flaw.py", line 10, in create_app
      non_site_files = _filter_site_files(monitored_files)
TypeError: _filter_site_files() takes exactly 2 arguments (1 given)
"""



def _filter_site_files(paths):
    if not paths:
        return []
    site_dir = os.path.dirname(os.__file__)
    return [fn for fn in paths if not fn.startswith(site_dir)]
