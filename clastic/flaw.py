from __future__ import unicode_literals

import os
import re
from core import Application
from render import AshesRenderFactory


def create_app(traceback_string, monitored_files=None):
    non_site_files = _filter_site_files(monitored_files)
    parsed_tb = _ParsedTB.from_string(traceback_string)
    resources = {'tb_str': traceback_string,
                 'parsed_error': parsed_tb,
                 'all_mon_files': monitored_files,
                 'mon_files': non_site_files}
    render_fact = AshesRenderFactory()
    render_fact.register_source('flaw_tmpl', _FLAW_TEMPLATE)
    routes = [('/', get_flaw_info, 'flaw_tmpl'),
              ('/<path:_ignored>', get_flaw_info, 'flaw_tmpl')]

    app = Application(routes, resources, render_fact)
    return app


def get_flaw_info(tb_str, parsed_error, mon_files):
    return {'exc_type': parsed_error.exc_type,
            'exc_msg': parsed_error.exc_msg,
            'mon_files': mon_files,
            'err': parsed_error,
            'tb_str': tb_str}


_FLAW_TEMPLATE = """\
<html>
  <head>
    <title>Oh, Flaw'd: {exc_type} in {err.source_file}</title>
  </head>
  <body>
    <h1>Whopps!</h1>

    <p>Clastic detected a modification, but couldn't restart your application. This is usually the result of a module-level error that prevents one of your application's modules from being imported. Fix the error and try refreshing the page.</p>

    <h2>{exc_type}: {exc_msg}</h2>
    <h3>Stack trace</h3>
    <pre>{tb_str}</pre>
    <br><hr>
    <p>Monitoring:<ul>{#mon_files}<li>{.}</li>{/mon_files}</ul></p>
  </body>
</html>
"""

_frame_re = re.compile(r'^File "(?P<filepath>.+)", line (?P<lineno>\d+)'
                       r', in (?P<funcname>.+)$')
_se_frame_re = re.compile(r'^File "(?P<filepath>.+)", line (?P<lineno>\d+)')


class _ParsedTB(object):
    def __init__(self, exc_type_name, exc_msg, frames=None):
        self.exc_type = exc_type_name
        self.exc_msg = exc_msg
        self.frames = list(frames or [])

    @property
    def source_file(self):
        try:
            return self.frames[-1]['filepath']
        except IndexError:
            return None

    @classmethod
    def from_string(cls, tb_str):
        if not isinstance(tb_str, unicode):
            tb_str = tb_str.decode('utf-8')
        tb_lines = tb_str.lstrip().splitlines()
        if tb_lines[0].strip() == 'Traceback (most recent call last):':
            frame_lines = tb_lines[1:-1]
            frame_re = _frame_re
        elif tb_lines[-1].startswith('SyntaxError'):
            frame_lines = tb_lines[:-2]
            frame_re = _se_frame_re
        else:
            raise ValueError('unrecognized traceback string format')
        exc_str = tb_lines[-1]
        exc_type, _, exc_msg = exc_str.partition(':')

        frames = []
        for pair_idx in range(0, len(frame_lines), 2):
            frame_line = frame_lines[pair_idx].strip()
            frame_dict = frame_re.match(frame_line).groupdict()
            frame_dict['source_line'] = frame_lines[pair_idx + 1].strip()
            frames.append(frame_dict)

        return cls(exc_type, exc_msg, frames)


def _filter_site_files(paths):
    if not paths:
        return []
    site_dir = os.path.dirname(os.__file__)
    return [fn for fn in paths if not fn.startswith(site_dir)]


if __name__ == '__main__':
    _example_tb = """
Traceback (most recent call last):
  File "example.py", line 2, in <module>
    plarp
NameError: name 'plarp' is not defined
"""

    create_app(_example_tb, [__file__]).serve()
