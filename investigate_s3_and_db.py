#!/usr/bin/env python3
"""
S3 버킷과 Render DB 조사 스크립트
"""
import boto3
import os
import sys
from pathlib import Path

# Django 환경 설정
sys.path.insert(0, str(Path(__file__).parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# .env 파일 로드
from dotenv import load_dotenv
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

import django
django.setup()

from django.conf import settings
from requests.models import Request, File

def check_is_temporary_status():
    """특정 Request들의 is_temporary 상태 확인"""
    print(f"\n{'='*80}")
    print("Request is_temporary 상태 조사")
    print(f"{'='*80}")

    try:
        # '죠지 - 오래오래' 파일만 확인 (더 구체적으로)
        problem_files = File.objects.filter(
            original_name__icontains='죠지'
        ).select_related('request')

        print(f"\n'죠지' 포함 파일들 (총 {problem_files.count()}개):")
        for f in problem_files:
            if f.request:
                print(f"  파일: {f.original_name}")
                print(f"    - File ID: {f.id}")
                print(f"    - Request ID: {f.request.id}")
                print(f"    - is_temporary: {f.request.is_temporary}")
                print(f"    - Order ID: {f.request.order_id}")
                print()

        # is_temporary=False인 Request 통계
        total_requests = Request.objects.count()
        temp_requests = Request.objects.filter(is_temporary=True).count()
        non_temp_requests = Request.objects.filter(is_temporary=False).count()

        print(f"\nRequest 통계:")
        print(f"  - 전체: {total_requests}개")
        print(f"  - is_temporary=True: {temp_requests}개")
        print(f"  - is_temporary=False: {non_temp_requests}개")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

def main():
    print("\n🔍 is_temporary 상태 조사 시작...")

    # is_temporary 상태 확인
    check_is_temporary_status()

    print("\n✅ 조사 완료!")

if __name__ == '__main__':
    main()
