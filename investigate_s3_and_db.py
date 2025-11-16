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
    print("DB 파일 전체 조사")
    print(f"{'='*80}")

    try:
        # 전체 파일 개수 확인
        total_files = File.objects.count()
        print(f"\n전체 파일 개수: {total_files}개")

        # 최근 파일 20개 확인
        recent_files = File.objects.select_related('request').order_by('-id')[:20]
        print(f"\n최근 파일 20개:")
        for f in recent_files:
            req_info = f"Request ID: {f.request.id}, Order: {f.request.order_id}" if f.request else "Request 없음"
            print(f"  [{f.id}] {f.original_name[:50]}... - {req_info}")

        print(f"\n{'='*80}")
        print("'죠지' 검색 결과")
        print(f"{'='*80}")

        # '죠지'로 검색
        joji_files = File.objects.filter(
            original_name__icontains='죠지'
        ).select_related('request')

        print(f"\n파일명에 '죠지' 포함: {joji_files.count()}개")
        for f in joji_files:
            if f.request:
                print(f"  파일: {f.original_name}")
                print(f"    - File ID: {f.id}")
                print(f"    - Request ID: {f.request.id}")
                print(f"    - is_temporary: {f.request.is_temporary}")
                print(f"    - Order ID: {f.request.order_id}")
                print()

        # 직접 ID로 확인 (File ID 32, 35, 36)
        print(f"\n직접 File ID로 확인:")
        for file_id in [32, 35, 36]:
            try:
                f = File.objects.get(id=file_id)
                print(f"\n  File ID {file_id}:")
                print(f"    파일명: {f.original_name}")
                print(f"    파일명 길이: {len(f.original_name)}")
                print(f"    파일명 바이트: {f.original_name.encode('utf-8')[:50]}")
                print(f"    '죠지' in 파일명: {'죠지' in f.original_name}")
                if f.request:
                    print(f"    Request ID: {f.request.id}")
            except File.DoesNotExist:
                print(f"  File ID {file_id}: 존재하지 않음")

        # 화자 이름에 '죠지' 포함된 Request
        print(f"\n화자 이름에 '죠지' 포함된 Request:")
        joji_requests = Request.objects.filter(speaker_names__icontains='죠지')
        print(f"총 {joji_requests.count()}개")
        for req in joji_requests[:5]:
            print(f"  Request ID: {req.id}, Order: {req.order_id}")
            print(f"    화자: {req.speaker_names}")
            files = req.files.all()
            for f in files:
                print(f"    파일: {f.original_name[:60]}")
            print()

        # Request 통계
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
