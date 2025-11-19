#!/usr/bin/env python
"""
PostgreSQL에 저장된 모든 파일 및 요청 정보 조회
"""
import os
import sys
import django

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
os.environ['USE_PRODUCTION_DB'] = 'True'  # 프로덕션 DB 강제 사용

django.setup()

from requests.models import Request, File

print("=" * 80)
print("PostgreSQL에 저장된 모든 데이터 조회")
print("=" * 80)

# 모든 Request 조회
print("\n" + "=" * 80)
print("📋 전체 Requests (11개)")
print("=" * 80)
requests = Request.objects.all().order_by('-created_at')

for idx, req in enumerate(requests, 1):
    print(f"\n[{idx}] Order ID: {req.order_id}, Request ID: {req.request_id}")
    print(f"    이름: {req.name}")
    print(f"    이메일: {req.email}")
    print(f"    전화: {req.phone}")
    print(f"    생성일: {req.created_at}")
    print(f"    Status: {req.status}, Order Status: {req.order_status}")
    print(f"    is_temporary: {req.is_temporary}")

    # 연결된 파일들 조회
    files = req.files.all()
    if files.exists():
        print(f"    📎 연결된 파일 ({files.count()}개):")
        for f in files:
            print(f"       - {f.original_name} ({f.file_size:,} bytes)")
            print(f"         S3 Key: {f.file}")

# 모든 File 조회
print("\n" + "=" * 80)
print("📁 전체 Files (18개)")
print("=" * 80)
files = File.objects.all().order_by('-created_at')

for idx, f in enumerate(files, 1):
    print(f"\n[{idx}] ID: {f.id}")
    print(f"    파일명: {f.original_name}")
    print(f"    파일 타입: {f.file_type}")
    print(f"    파일 크기: {f.file_size:,} bytes ({f.file_size / 1024 / 1024:.2f} MB)")
    print(f"    S3 Key: {f.file}")
    print(f"    생성일: {f.created_at}")

    if f.request:
        print(f"    연결된 Request: {f.request.request_id} ({f.request.name})")
    else:
        print(f"    연결된 Request: 없음")

print("\n" + "=" * 80)
print("조회 완료")
print("=" * 80)
