#!/usr/bin/env python
import os
import django

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from requests.models import Request
from notification_service.notification_service import notification_service

# Request 객체 가져오기
request_obj = Request.objects.get(id=25)
print(f"Request: {request_obj.name} ({request_obj.email})")

# 알림 발송 테스트
print("=== 알림 발송 테스트 ===")
notification_settings = notification_service.get_notification_settings('in_progress')
print(f"Notification settings: {notification_settings}")

result = notification_service.send_status_notification(
    request_obj,
    'in_progress',
    'received',
    send_sms=notification_settings['sms'],
    send_email=notification_settings['email']
)

print(f"Result: {result}")
print(f"Success: {result['success']}")