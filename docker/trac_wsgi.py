#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import os
import logging

sys.stdout = sys.stderr

#logger = logging.getLogger(__name__)
gunicorn_logger = logging.getLogger('gunicorn.error')
gunicorn_debug = int(os.getenv('GUNICORN_DEBUG', '0'))

script_dir = os.path.dirname(os.path.realpath(__file__))
trac_env_dir = os.path.join(script_dir, 'env')
#put here your ENV's Variables
# here is an example with multiple instances
os.environ['TRAC_ENV'] = trac_env_dir
os.environ['PYTHON_EGG_CACHE'] = os.path.join(script_dir, '.eggs')

TRAC_BASE_PATH = os.getenv('TRAC_BASE_PATH', '/')

import trac.web.main
def gunicorn_dispatch_request(environ, start_response):
    if gunicorn_debug:
        gunicorn_logger.info('gunicorn_dispatch_request pre: %s' % environ)
    # get the original path or the request; e.g. /trac/login
    path = environ.get('PATH_INFO', '')
    base_path = environ.get('HTTP_TRAC_BASE_PATH', TRAC_BASE_PATH)

    if path.startswith(base_path):
        # remove the base_path prefix; e.g. /trac and keep the rest /login
        environ['PATH_INFO'] = path[len(base_path):]
        # put the fixed base path as SCRIPT_NAME so trac can automatically determine
        # the prefix and correctly generate and handle URLs
        environ['SCRIPT_NAME'] = base_path

    # handle username with REALM notation; e.g. foo@BAR
    if 'HTTP_REMOTE_USER' in environ:
        environ['REMOTE_USER'] = environ['HTTP_REMOTE_USER']
    if 'REMOTE_USER' in environ and '@' in environ['REMOTE_USER']:
        # drop the REALM part from the username
        (environ['REMOTE_USER'], realm) = environ['REMOTE_USER'].split('@', 1)
    if gunicorn_debug:
        gunicorn_logger.info('gunicorn_dispatch_request post: %s' % environ)
    return trac.web.main.dispatch_request(environ, start_response)

application = gunicorn_dispatch_request

