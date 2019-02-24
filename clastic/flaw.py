# -*- coding: utf-8 -*-
"""The Flaw application is a minimalist tool to enable rapid
development, even in the face of inevitable errors.

Flaw is a small WSGI application, itself built on Clastic, which
activates when the development server cannot start, due to a
SyntaxError, or other import-time error. Flaw displays the error
message, stack trace, and the files which are monitored.

Once the error is corrected, and the monitored file is saved, Clastic
will shut down Flaw and restart your application. This is to avoid
having to check console output and manually restart your application
due to typos and other common errors.
"""

import os
import re
import ast

from .application import Application
from .static import StaticApplication
from .render import AshesRenderFactory


_CUR_PATH = os.path.dirname(os.path.abspath(__file__))
_ASSET_PATH = os.path.join(_CUR_PATH, '_clastic_assets')


def create_app(traceback_string, monitored_files=None):
    if monitored_files:
        monitored_files.sort(key=lambda x: len(x))
    non_site_files = _filter_site_files(monitored_files)
    try:
        parsed_tb = _ParsedTB.from_string(traceback_string)
        parsed_error = parsed_tb.to_dict()
    except:
        parsed_error = {}
    resources = {'tb_str': traceback_string,
                 'parsed_error': parsed_error,
                 'all_mon_files': monitored_files,
                 'mon_files': non_site_files}
    arf = AshesRenderFactory()
    arf.register_source('flaw_tmpl', _FLAW_TEMPLATE)
    routes = [('/', get_flaw_info, 'flaw_tmpl'),
              ('/clastic_assets/', StaticApplication(_ASSET_PATH)),
              ('/<_ignored*>', get_flaw_info, 'flaw_tmpl')]

    app = Application(routes, resources, render_factory=arf)
    return app


def get_flaw_info(tb_str, parsed_error, all_mon_files, mon_files):
    try:
        last_line = tb_str.splitlines()[-1]
    except:
        last_line = u'Unknown error'
    return {'mon_files': mon_files,
            'all_mon_files': all_mon_files,
            'parsed_err': parsed_error,
            'last_line': last_line,
            'tb_str': tb_str}


_FLAW_TEMPLATE = u"""\
<!doctype html>
<html>
  <head>
    <title>Oh, Flaw'd{#parsed_err}: {exc_type} in {source_file}{/parsed_err}</title>
    <link rel="stylesheet" type="text/css" href="/clastic_assets/normalize.css">
    <link rel="stylesheet" type="text/css" href="/clastic_assets/common.css">
  </head>
  <body>
    <h1 class="page_title">Whopps!</h1>

    <p>Clastic detected a modification, but couldn't restart your application. This is often the result of a module-level error that prevents one of your application's modules from being imported. Fix the error and try refreshing the page.</p>

    {#parsed_err}
      <h2 class="parsed-error-h2">{exc_type}<p>{exc_msg}</p></h2>
    {:else}
      <h2 class="unparsed-error-h2">{last_line}</h2>
    {/parsed_err}
    <h2>Stack trace</h2>
    <pre>{tb_str}</pre>
    <br><hr>
    <p>Monitoring:
      <ul>{#mon_files}<li>{.}</li>{/mon_files}</ul>
      <ul id="all_files" style="display:none;">{#all_mon_files}<li>{.}</li>{/all_mon_files}</ul>
    </p>
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

    def to_dict(self):
        return {'exc_type': self.exc_type,
                'exc_msg': self.exc_msg,
                'frames': self.frames}

    @classmethod
    def from_string(cls, tb_str):
        if not isinstance(tb_str, unicode):
            tb_str = tb_str.decode('utf-8')
        tb_lines = tb_str.lstrip().splitlines()
        if tb_lines[0].strip() == 'Traceback (most recent call last):':
            frame_lines = tb_lines[1:-1]
            frame_re = _frame_re
        elif len(tb_lines) > 1 and tb_lines[-2].lstrip().startswith('^'):
            frame_lines = tb_lines[:-2]
            frame_re = _se_frame_re
        else:
            raise ValueError('unrecognized traceback string format')
        while tb_lines:
            cl = tb_lines[-1]
            if cl.startswith('Exception ') and cl.endswith('ignored'):
                # handle some ignored exceptions
                tb_lines.pop()
            else:
                break
        for line in reversed(tb_lines):
            # get the bottom-most line that looks like an actual Exception
            # repr(), (i.e., "Exception: message")
            exc_type, sep, exc_msg = line.partition(':')
            if sep and exc_type and len(exc_type.split()) == 1:
                break

        frames = []
        for pair_idx in range(0, len(frame_lines), 2):
            frame_line = frame_lines[pair_idx].strip()
            frame_match = frame_re.match(frame_line)
            if frame_match:
                frame_dict = frame_match.groupdict()
            else:
                continue
            frame_dict['source_line'] = frame_lines[pair_idx + 1].strip()
            frames.append(frame_dict)

        return cls(exc_type, exc_msg, frames)


def _filter_site_files(paths):
    ret = paths or []
    if not paths:
        return ret
    main_lib_dir = os.path.dirname(ast.__file__)
    ret = [fn for fn in ret if not fn.startswith(main_lib_dir)]
    venv_lib_dir = os.path.dirname(os.__file__)
    ret = [fn for fn in ret if not fn.startswith(venv_lib_dir)]
    try:
        import werkzeug
        venv_site_dir = os.path.dirname(werkzeug.__file__)
        ret = [fn for fn in ret if not fn.startswith(venv_site_dir)]
    except:
        pass
    try:
        import clastic
        clastic_dir = os.path.dirname(clastic.__file__)
        ret = [fn for fn in ret if not fn.startswith(clastic_dir)]
    except:
        pass

    return ret


if __name__ == '__main__':
    _example_tb = u"""
Traceback (most recent call last):
  File "example.py", line 2, in <module>
    plarp
NameError: name 'plarp' is not defined
"""
    create_app(_example_tb, [__file__]).serve()
