#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import os

sys.stdout = sys.stderr

script_dir = os.path.dirname(os.path.realpath(__file__))
trac_env_dir = os.path.join(script_dir, 'env')
#put here your ENV's Variables
# here is an example with multiple instances
os.environ['TRAC_ENV'] = trac_env_dir
os.environ['PYTHON_EGG_CACHE'] = os.path.join(script_dir, '.eggs')

TRAC_BASE_PATH = '/'

import trac.web.main
def gunicorn_dispatch_request(environ, start_response):
    path = environ['SCRIPT_NAME'] + environ.get('PATH_INFO', '')
    #environ['PATH_INFO'] = path[len(TRAC_BASE_PATH):]
    environ['PATH_INFO'] = path
    environ['SCRIPT_NAME'] = TRAC_BASE_PATH
    print(environ['SCRIPT_NAME'], environ['PATH_INFO'])
    if 'HTTP_REMOTE_USER' in environ:
        environ['REMOTE_USER'] = environ['HTTP_REMOTE_USER']
    if 'REMOTE_USER' in environ and '@' in environ['REMOTE_USER']:
        (environ['REMOTE_USER'], realm) = environ['REMOTE_USER'].split('@', 1)
    return trac.web.main.dispatch_request(environ, start_response)

application = gunicorn_dispatch_request

