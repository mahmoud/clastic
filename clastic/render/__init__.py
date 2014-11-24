
from simple import (BasicRender,
                    JSONRender,
                    JSONPRender,
                    render_json,
                    render_json_dev,
                    render_basic)
from tabular import Table, TabularRender


# TODO: deprecate
from simple import (json_response,
                    dev_json_response,
                    default_response)

try:
    import ashes
except ImportError:
    import _ashes as ashes

from ashes_templates import AshesRenderFactory

__all__ = ('JSONRender',
           'JSONPRender',
           'render_json',
           'render_json_dev',
           'render_basic',
           'dev_json_response',
           'json_response',
           'default_response',
           'AshesRenderFactory')
