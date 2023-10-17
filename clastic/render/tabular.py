# -*- coding: utf-8 -*-

import os
import re
from textwrap import dedent
try:
    from html import escape as html_escape
except ImportError:
    from cgi import escape as html_escape


from boltons.tableutils import Table
from boltons.urlutils import find_all_links
from werkzeug.wrappers import Response

from ..sinter import get_callable_labels

_CUR_PATH = os.path.dirname(os.path.abspath(__file__))
_CSS_PATH = _CUR_PATH + '/../_clastic_assets/common.css'
try:
    _STYLE_CONTENT = open(_CSS_PATH).read()
except Exception:
    _STYLE_CONTENT = ''


def escape_html(text):
    return html_escape(text, True)


# URL parsing regex (based on RFC 3986 Appendix B, with modifications)
_URL_RE = re.compile(r'^((?P<scheme>[^:/?#]+):)?'
                     r'((?P<_netloc_sep>//)(?P<authority>[^/?#]*))?'
                     r'(?P<path>[^?#]*)'
                     r'(\?(?P<query>[^#]*))?'
                     r'(#(?P<fragment>.*))?')

# heuristic url re
_FIND_ALL_URL_RE = re.compile(r"""\b((?:([\w-]+):(/{1,3})|www[.])(?:(?:(?:[^\s&()<>]|&amp;|&quot;)*(?:[^!"#$%'()*+,.:;<=>?@\[\]^`{|}~\s]))|(?:\((?:[^\s&()]|&amp;|&quot;)*\)))+)""")


def linkify(text, default_scheme='https', schemes=()):
    "heuristically find and replace links with html hyperlinks"
    prev_end, start, end = 0, None, None
    ret = []
    _add = ret.append

    for match in _FIND_ALL_URL_RE.finditer(text):
        start, end = match.start(1), match.end(1)
        if prev_end < start:
            _add(text[prev_end:start])
        prev_end = end

        cur_url_text = match.group(0)
        url_match = _URL_RE.match(cur_url_text)
        if not url_match or not url_match.group('scheme'):
            if not default_scheme:
                _add(text[start:end])
                continue
            cur_url_text = default_scheme + '://' + cur_url_text
        elif schemes and url_match.group('scheme') not in schemes:
            _add(text[start:end])
            continue

        cur_url_anchor = '<a href="{0}">{0}</a>'.format(cur_url_text)
        _add(cur_url_anchor)

    tail = text[prev_end:]
    if tail:
        _add(tail)

    return u''.join(ret)


class TabularRender(object):
    default_table_type = Table

    _html_doctype = '<!doctype html>'
    _html_wrapper, _html_wrapper_close = '<html>', '</html>'
    _html_table_tag = '<table class="clastic-atr-table">'
    _html_style_content = _STYLE_CONTENT

    def __init__(self, max_depth=4, orientation='auto', **kwargs):
        self.max_depth = max_depth
        self.orientation = orientation
        self.enable_title = kwargs.pop('enable_title', True)
        self.table_type = kwargs.pop('table_type', self.default_table_type)
        self.with_metadata = kwargs.pop('with_metadata', True)

    def _html_format_ep(self, route):
        ctx_label, func_name, argstr = get_callable_labels(route.endpoint)
        func_name = func_name.replace('<', '(').replace('>', ')')

        func_doc = getattr(route.endpoint, '__doc__', '')
        if func_doc:
            # Dedentation that accounts for first line indentation difference
            lines = func_doc.splitlines()
            first_line, remainder = lines[0], '\n'.join(lines[1:])
            dedented = dedent(first_line) + '\n' + dedent(remainder)
            escaped_doc = linkify(escape_html(dedented))
            html_doc = '<p style="white-space: pre;">%s</p>' % escaped_doc
        else:
            html_doc = '<!-- add a docstring to display a message here! -->'

        title = ('<h2><small><sub>%s</sub></small><br/>%s(%s)</h2>%s'
                 % (ctx_label, func_name, argstr, html_doc))
        return title

    def context_to_response(self, context, _route=None):
        content_parts = [self._html_wrapper]
        if self._html_style_content:
            content_parts.extend(['<head><style type="text/css">',
                                  self._html_style_content,
                                  '</style></head>'])
        content_parts.append('<body>')

        if _route:
            title = self._html_format_ep(_route)
            content_parts.append(title)

        if isinstance(context, self.table_type):
            table = context
        else:
            table = self.table_type.from_data(context,
                                              max_depth=self.max_depth)
        table._html_table_tag = self._html_table_tag
        content = table.to_html(max_depth=self.max_depth,
                                orientation=self.orientation,
                                with_metadata=self.with_metadata)
        content_parts.append(content)
        content_parts.append('</body>')
        content_parts.append(self._html_wrapper_close)
        return Response('\n'.join(content_parts), mimetype='text/html')

    __call__ = context_to_response
