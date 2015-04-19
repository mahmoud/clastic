# -*- coding: utf-8 -*-

"""
    clastic
    ~~~~~~~

    A functional Python web framework that streamlines explicit
    development practices while eliminating global state.

    :copyright: (c) 2013 by Mahmoud Hashemi
    :license: BSD, see LICENSE for more details.

"""

import sys
from setuptools import setup


__author__ = 'Mahmoud Hashemi'
__version__ = '0.4.3'
__contact__ = 'mahmoudrhashemi@gmail.com'
__url__ = 'https://github.com/mahmoud/clastic'
__license__ = 'BSD'

desc = ('A functional Python web framework that streamlines'
        ' explicit development practices while eliminating'
        ' global state.')

if sys.version_info < (2,6):
    raise NotImplementedError("Sorry, clastic only supports Python >=2.6")

if sys.version_info >= (3,):
    raise NotImplementedError("clastic Python 3 support en route to your location")

setup(name='clastic',
      version=__version__,
      description=desc,
      long_description=__doc__,
      author=__author__,
      author_email=__contact__,
      url=__url__,
      packages=['clastic',
                'clastic.render',
                'clastic.middleware',
                'clastic.contrib',
                'clastic.tests'],
      include_package_data=True,
      zip_safe=False,
      install_requires=['Werkzeug==0.9.4', 'argparse>=1.2.1'],
      license=__license__,
      platforms='any',
      classifiers=[
          'Intended Audience :: Developers',
          'Topic :: Internet :: WWW/HTTP :: HTTP Servers',
          'Topic :: Internet :: WWW/HTTP :: WSGI',
          'Topic :: Internet :: WWW/HTTP :: WSGI :: Application',
          'Topic :: Internet :: WWW/HTTP :: WSGI :: Middleware',
          'Topic :: Internet :: WWW/HTTP :: WSGI :: Server',
          'Topic :: Internet :: WWW/HTTP :: Dynamic Content :: CGI Tools/Libraries',
          'Topic :: Software Development :: Libraries :: Application Frameworks',
          'Programming Language :: Python :: 2.6',
          'Programming Language :: Python :: 2.7', ]
      )
