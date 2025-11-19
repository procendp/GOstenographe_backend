#!/usr/bin/env python
"""
고아 파일 정리 스크립트
- S3에는 있지만 PostgreSQL에 없는 파일
- PostgreSQL에는 있지만 S3에 없는 파일
- Request와 연결되지 않은 File 레코드 (단, transcripts/ 제외)
"""
import os
import sys
import django
from datetime import datetime, timedelta

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
os.environ['USE_PRODUCTION_DB'] = 'True'

django.setup()

import boto3
from django.conf import settings
from requests.models import File

print("=" * 80)
print("🧹 고아 파일 정리")
print("=" * 80)

# S3 클라이언트 초기화
s3_client = boto3.client(
    's3',
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    region_name=settings.AWS_S3_REGION_NAME
)

# 1. S3의 모든 파일 키 가져오기
print("\n1️⃣ S3 파일 목록 조회 중...")
s3_files = set()
paginator = s3_client.get_paginator('list_objects_v2')

try:
    for page in paginator.paginate(Bucket=settings.AWS_STORAGE_BUCKET_NAME):
        if 'Contents' in page:
            for obj in page['Contents']:
                s3_files.add(obj['Key'])
    print(f"   ✅ S3 파일 수: {len(s3_files)}개")
except Exception as e:
    print(f"   ❌ S3 조회 실패: {str(e)}")
    sys.exit(1)

# 2. PostgreSQL의 모든 파일 키 가져오기
print("\n2️⃣ PostgreSQL 파일 목록 조회 중...")
db_files = {}
for f in File.objects.all():
    db_files[f.file] = f
print(f"   ✅ PostgreSQL 파일 수: {len(db_files)}개")

# 3. 고아 파일 찾기
print("\n" + "=" * 80)
print("고아 파일 분석 결과")
print("=" * 80)

# 타입 A: S3에만 있는 파일 (PostgreSQL에 없음)
orphan_s3 = s3_files - set(db_files.keys())
print(f"\n📁 타입 A - S3에만 있는 파일: {len(orphan_s3)}개")
if orphan_s3:
    for i, key in enumerate(list(orphan_s3)[:10], 1):
        print(f"   {i}. {key}")
    if len(orphan_s3) > 10:
        print(f"   ... 외 {len(orphan_s3) - 10}개")

# 타입 B: PostgreSQL에만 있는 파일 (S3에 없음)
orphan_db = set(db_files.keys()) - s3_files
print(f"\n💾 타입 B - PostgreSQL에만 있는 파일: {len(orphan_db)}개")
if orphan_db:
    for i, key in enumerate(list(orphan_db)[:10], 1):
        file_obj = db_files[key]
        print(f"   {i}. ID: {file_obj.id}, Key: {key}")
    if len(orphan_db) > 10:
        print(f"   ... 외 {len(orphan_db) - 10}개")

# 타입 C: 진짜 고아 파일 (request도 없고 transcript_requests도 없음)
# File.is_orphan() 메서드 사용
all_files = File.objects.all()
true_orphans = []
for f in all_files:
    if f.is_orphan():
        true_orphans.append(f)

print(f"\n🔗 타입 C - 진짜 고아 파일 (일반 첨부도 아니고 속기록도 아님): {len(true_orphans)}개")
if true_orphans:
    for i, f in enumerate(true_orphans[:10], 1):
        print(f"   {i}. ID: {f.id}, 파일명: {f.original_name}, S3 Key: {f.file}")
        # 연결 상태 확인
        print(f"      request: {f.request}, transcript_requests: {f.transcript_requests.count()}개")
    if len(true_orphans) > 10:
        print(f"   ... 외 {len(true_orphans) - 10}개")

# 4. 정리 제안
print("\n" + "=" * 80)
print("정리 제안")
print("=" * 80)

total_orphans = len(orphan_s3) + len(orphan_db) + len(true_orphans)

if total_orphans == 0:
    print("\n✅ 고아 파일이 없습니다! 깨끗한 상태입니다.")
else:
    print(f"\n⚠️  총 {total_orphans}개의 고아 파일이 발견되었습니다.")
    print("\n다음 명령어로 정리할 수 있습니다:")
    print("\n  1. 타입 A 정리 (S3에서 삭제):")
    print("     python cleanup_orphan_files.py --clean-s3")
    print("\n  2. 타입 B 정리 (PostgreSQL에서 삭제):")
    print("     python cleanup_orphan_files.py --clean-db")
    print("\n  3. 타입 C 정리 (Request 없는 파일 삭제):")
    print("     python cleanup_orphan_files.py --clean-orphan-records")
    print("\n  4. 모두 정리:")
    print("     python cleanup_orphan_files.py --clean-all")

print("\n" + "=" * 80)
print("완료")
print("=" * 80)

# 실제 정리 기능 (명령어 인자로 실행)
if len(sys.argv) > 1:
    action = sys.argv[1]

    if action == '--clean-s3' or action == '--clean-all':
        print("\n🗑️  S3에서 고아 파일 삭제 중...")
        for key in orphan_s3:
            try:
                s3_client.delete_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=key)
                print(f"   ✅ 삭제: {key}")
            except Exception as e:
                print(f"   ❌ 실패: {key} - {str(e)}")

    if action == '--clean-db' or action == '--clean-all':
        print("\n🗑️  PostgreSQL에서 고아 레코드 삭제 중...")
        for key in orphan_db:
            file_obj = db_files[key]
            try:
                # S3 파일이 없으므로 S3 삭제는 스킵하고 DB만 삭제
                file_obj.delete(skip_s3_delete=True) if hasattr(file_obj.delete, 'skip_s3_delete') else File.objects.filter(id=file_obj.id).delete()
                print(f"   ✅ 삭제: ID {file_obj.id} - {key}")
            except Exception as e:
                print(f"   ❌ 실패: ID {file_obj.id} - {str(e)}")

    if action == '--clean-orphan-records' or action == '--clean-all':
        print("\n🗑️  진짜 고아 파일 레코드 삭제 중...")
        print("   (속기록 완성 파일은 보호됩니다)")
        count = 0
        for f in true_orphans:
            try:
                # is_orphan()으로 한번 더 확인 (안전장치)
                if f.is_orphan():
                    f.delete()  # S3 파일도 함께 삭제
                    count += 1
                    print(f"   ✅ 삭제: ID {f.id} - {f.original_name}")
                else:
                    print(f"   ⚠️  건너뜀 (연결된 파일): ID {f.id} - {f.original_name}")
            except Exception as e:
                print(f"   ❌ 실패: ID {f.id} - {str(e)}")
        print(f"\n   총 {count}개 삭제 완료")
