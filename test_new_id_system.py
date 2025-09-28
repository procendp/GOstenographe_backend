#!/usr/bin/env python
import os
import sys
import django

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from requests.models import Request
from datetime import datetime

def test_new_id_system():
    """새로운 ID 시스템 테스트"""
    print("=" * 60)
    print("새로운 ID 시스템 테스트")
    print("=" * 60)
    
    # 기존 데이터 확인
    existing_requests = Request.objects.all().order_by('-created_at')[:5]
    if existing_requests:
        print("\n📋 기존 요청서 (최근 5개):")
        for req in existing_requests:
            print(f"  - Order ID: {req.order_id}, Request ID: {req.request_id}")
    
    print("\n🔄 새로운 ID 생성 테스트:")
    
    # 다음 Order 카운터 확인
    next_counter = Request.get_next_order_counter()
    print(f"  - 다음 주문 카운터: {next_counter:02d}")
    
    # Order ID 생성 테스트
    test_order_id = Request.generate_order_id()
    print(f"  - 생성될 Order ID: {test_order_id}")
    
    # Request ID 생성 테스트 (같은 Order ID로 여러 파일)
    print(f"\n📁 같은 주문에 여러 파일이 있는 경우:")
    for i in range(3):
        test_request_id = f"{test_order_id}{i:02d}"
        print(f"  - 파일 {i+1}: Request ID = {test_request_id}")
    
    # 99에서 00으로 리셋되는 시나리오
    print(f"\n🔄 카운터 리셋 시나리오 (99 → 00):")
    
    # 가상의 99번 주문
    date_str = datetime.now().strftime('%y%m%d')
    order_99 = f"{date_str}99"
    print(f"  - 99번째 주문: Order ID = {order_99}")
    print(f"    - Request ID = {order_99}00 (파일 1개)")
    
    # 다음은 00으로 리셋
    order_00 = f"{date_str}00"
    print(f"  - 100번째 주문 (리셋): Order ID = {order_00}")
    print(f"    - Request ID = {order_00}00, {order_00}01 (파일 2개)")
    
    print("\n✅ ID 시스템 테스트 완료!")
    print("=" * 60)

if __name__ == "__main__":
    test_new_id_system()