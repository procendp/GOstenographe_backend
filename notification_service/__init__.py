# Notification Service for GOstenographe

# CRITICAL: HTTP requests 라이브러리를 먼저 로드 (Django requests 앱과 충돌 방지)
import sys
import requests as _http_requests_lib
sys.modules['_http_lib'] = _http_requests_lib