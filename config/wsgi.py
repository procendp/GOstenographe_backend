"""
WSGI config for config project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os

# CRITICAL: HTTP requests 라이브러리를 Django 로드 전에 먼저 import
import sys
import requests as _http_requests_lib
sys.modules['http_lib'] = _http_requests_lib

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_wsgi_application()
