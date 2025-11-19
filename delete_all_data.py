#!/usr/bin/env python
"""
PostgreSQL 데이터베이스 전체 데이터 삭제
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
print("⚠️  PostgreSQL 데이터베이스 전체 데이터 삭제")
print("=" * 80)

# 삭제 전 현재 상태 확인
requests_count = Request.objects.count()
files_count = File.objects.count()

print(f"\n현재 데이터:")
print(f"  - Requests: {requests_count}개")
print(f"  - Files: {files_count}개")

print("\n🗑️  모든 데이터를 삭제합니다...\n")

# 1. 모든 File 삭제
print("1️⃣ Files 삭제 중...")
deleted_files = File.objects.all().delete()
print(f"   ✅ Files 삭제 완료: {deleted_files[0]}개")

# 2. 모든 Request 삭제
print("\n2️⃣ Requests 삭제 중...")
deleted_requests = Request.objects.all().delete()
print(f"   ✅ Requests 삭제 완료: {deleted_requests[0]}개")

# 삭제 후 확인
print("\n" + "=" * 80)
print("삭제 완료 - 최종 확인")
print("=" * 80)

final_requests = Request.objects.count()
final_files = File.objects.count()

print(f"\n최종 데이터:")
print(f"  - Requests: {final_requests}개")
print(f"  - Files: {final_files}개")

if final_requests == 0 and final_files == 0:
    print("\n✅ 모든 데이터가 성공적으로 삭제되었습니다!")
else:
    print("\n⚠️  일부 데이터가 남아있습니다.")

print("\n" + "=" * 80)
print("참고: S3에 저장된 실제 파일은 별도로 삭제해야 합니다.")
print("=" * 80)
