#!/usr/bin/env python
"""
PostgreSQL 시퀀스 리셋 (1부터 다시 시작)
"""
import os
import sys
import django

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
os.environ['USE_PRODUCTION_DB'] = 'True'  # 프로덕션 DB 강제 사용

django.setup()

from django.db import connection

print("=" * 80)
print("🔄 PostgreSQL 시퀀스 리셋")
print("=" * 80)

# 시퀀스 목록 조회 및 리셋
with connection.cursor() as cursor:
    # 모든 시퀀스 조회
    cursor.execute("""
        SELECT c.relname as sequence_name
        FROM pg_class c
        WHERE c.relkind = 'S'
        AND c.relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
        ORDER BY c.relname;
    """)

    sequences = cursor.fetchall()

    if sequences:
        print(f"\n총 {len(sequences)}개의 시퀀스를 리셋합니다:\n")

        for row in sequences:
            seq_name = row[0]

            # 시퀀스를 1로 리셋
            cursor.execute(f"ALTER SEQUENCE {seq_name} RESTART WITH 1;")
            print(f"  ✅ {seq_name} → 1로 리셋")

        print("\n" + "=" * 80)
        print("✅ 모든 시퀀스가 1로 리셋되었습니다!")
        print("=" * 80)

        # 리셋 확인
        print("\n리셋 확인:")
        for row in sequences:
            seq_name = row[0]
            cursor.execute(f"SELECT last_value FROM {seq_name};")
            last_value = cursor.fetchone()[0]
            print(f"  - {seq_name}: {last_value}")
    else:
        print("\n⚠️  시퀀스를 찾을 수 없습니다.")

print("\n" + "=" * 80)
print("다음 레코드는 ID 1부터 시작합니다.")
print("=" * 80)
