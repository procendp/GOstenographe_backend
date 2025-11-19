#!/usr/bin/env python
"""
Render PostgreSQL 데이터베이스 상태 확인 스크립트
"""
import os
import sys
import django

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
os.environ['USE_PRODUCTION_DB'] = 'True'  # 프로덕션 DB 강제 사용

django.setup()

from django.db import connection
from requests.models import Request, File

print("=" * 60)
print("Render PostgreSQL 데이터베이스 상태 확인")
print("=" * 60)

# 현재 데이터베이스 확인
with connection.cursor() as cursor:
    cursor.execute("SELECT current_database(), version();")
    db_info = cursor.fetchone()
    print(f"\n현재 데이터베이스: {db_info[0]}")
    print(f"PostgreSQL 버전: {db_info[1][:50]}...")

# Request 테이블 확인
print("\n" + "=" * 60)
print("Requests 테이블")
print("=" * 60)
requests = Request.objects.all()
print(f"총 레코드 수: {requests.count()}")

if requests.count() > 0:
    print("\n최근 5개:")
    for req in requests.order_by('-created_at')[:5]:
        print(f"  - Order ID: {req.order_id}, Request ID: {req.request_id}")
        print(f"    생성일: {req.created_at}, 이메일: {req.email}")

# File 테이블 확인
print("\n" + "=" * 60)
print("Files 테이블")
print("=" * 60)
files = File.objects.all()
print(f"총 레코드 수: {files.count()}")

if files.count() > 0:
    print("\n최근 5개:")
    for f in files.order_by('-created_at')[:5]:
        print(f"  - ID: {f.id}, S3 Key: {f.file}")
        print(f"    파일명: {f.original_name}, 생성일: {f.created_at}")

# 시퀀스 현재 값 확인 (과거 데이터 존재 여부)
print("\n" + "=" * 60)
print("시퀀스 현재 값 (과거 데이터 존재 여부 확인)")
print("=" * 60)

with connection.cursor() as cursor:
    cursor.execute("""
        SELECT
            c.relname as sequence_name,
            CASE
                WHEN pg_sequence_last_value(c.oid) IS NULL THEN 0
                ELSE pg_sequence_last_value(c.oid)
            END as last_value
        FROM pg_class c
        WHERE c.relkind = 'S'
        AND c.relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
        AND (c.relname LIKE '%request%' OR c.relname LIKE '%file%')
        ORDER BY c.relname;
    """)

    sequences = cursor.fetchall()
    if sequences:
        for row in sequences:
            print(f"\n{row[0]}: {row[1]}")
            if row[1] > 1:
                print(f"  ⚠️ 시퀀스가 {row[1]}까지 증가함 → 과거에 최소 {row[1]-1}개의 레코드가 있었음!")
            else:
                print(f"  ✅ 시퀀스 초기 상태 → 데이터가 한 번도 없었음")
    else:
        print("시퀀스를 찾을 수 없습니다.")

# 테이블 통계
print("\n" + "=" * 60)
print("테이블 통계 (삭제된 행 확인)")
print("=" * 60)

with connection.cursor() as cursor:
    cursor.execute("""
        SELECT
            relname as table_name,
            n_live_tup as live_rows,
            n_dead_tup as dead_rows,
            last_autovacuum
        FROM pg_stat_user_tables
        WHERE schemaname = 'public'
        AND (relname LIKE '%request%' OR relname LIKE '%file%')
        ORDER BY relname;
    """)

    stats = cursor.fetchall()
    if stats:
        for row in stats:
            print(f"\n{row[0]}:")
            print(f"  현재 행 수: {row[1]}")
            print(f"  삭제된 행 수: {row[2]}")
            print(f"  마지막 autovacuum: {row[3]}")

            if row[2] > 0:
                print(f"  ⚠️ {row[2]}개의 행이 최근 삭제됨!")

print("\n" + "=" * 60)
print("확인 완료")
print("=" * 60)
