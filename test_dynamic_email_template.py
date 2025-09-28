#!/usr/bin/env python
"""
동적 이메일 템플릿 시스템 테스트
"""
import os
import sys
import django

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from requests.models import Request
from notification_service.bulk_email_service import BulkEmailService

def test_dynamic_template_context():
    """동적 템플릿 컨텍스트 생성 테스트"""
    print("=" * 60)
    print("동적 이메일 템플릿 시스템 테스트")
    print("=" * 60)
    
    # 최근 요청 몇 개 가져오기
    recent_requests = Request.objects.all().order_by('-created_at')[:3]
    
    if not recent_requests:
        print("❌ 테스트할 요청 데이터가 없습니다.")
        return
    
    print(f"📋 테스트 대상 요청: {len(recent_requests)}개")
    for req in recent_requests:
        print(f"  - Request ID: {req.request_id}, Email: {req.email}, Name: {req.name}")
    
    # BulkEmailService 인스턴스 생성
    bulk_service = BulkEmailService()
    
    print("\n🔧 템플릿 컨텍스트 생성 테스트:")
    
    # 이메일별로 그룹화
    grouped = bulk_service.group_requests_by_email(recent_requests)
    print(f"  - 이메일별 그룹: {len(grouped)}개")
    
    for email, email_requests in grouped.items():
        print(f"\n📧 이메일: {email}")
        print(f"   요청 수: {len(email_requests)}개")
        
        # 템플릿 컨텍스트 생성
        context = bulk_service.create_template_context(email_requests)
        
        print("   🎯 생성된 템플릿 컨텍스트:")
        print(f"     - customer_name: {context.get('customer_name')}")
        print(f"     - order_id: {context.get('order_id')}")
        print(f"     - phone: {context.get('phone')}")
        print(f"     - email: {context.get('email')}")
        print(f"     - address: {context.get('address')}")
        print(f"     - final_option: {context.get('final_option')}")
        print(f"     - file_summary: {context.get('file_summary')}")
        print(f"     - uploaded_files: {len(context.get('uploaded_files', []))}개")
        
        # 파일 상세 정보
        if context.get('uploaded_files'):
            print("     📁 파일 목록:")
            for i, file_info in enumerate(context.get('uploaded_files', [])[:3]):  # 최대 3개만 표시
                print(f"       {i+1}. {file_info.get('name')} ({file_info.get('duration')})")
            if len(context.get('uploaded_files', [])) > 3:
                print(f"       ... 외 {len(context.get('uploaded_files', [])) - 3}개")
    
    print("\n✅ 동적 템플릿 시스템 테스트 완료!")
    print("\n📝 다음 단계:")
    print("  1. 실제 이메일 발송 테스트: bulk_service.send_emails_with_template(requests)")
    print("  2. 템플릿 렌더링 확인: render_to_string(template_name, context)")
    print("  3. 첨부파일 포함 발송 테스트")
    
    print("=" * 60)

def test_template_variables():
    """템플릿 변수 매핑 테스트"""
    print("\n🎨 템플릿 변수 매핑 확인:")
    
    template_variables = [
        '{{ customer_name }}',
        '{{ order_id }}', 
        '{{ phone }}',
        '{{ email }}',
        '{{ address }}',
        '{{ final_option }}',
        '{{ file_summary }}',
        '{% for file in uploaded_files %}',
        '{{ file.name }}',
        '{{ file.duration }}',
        '{% endfor %}'
    ]
    
    print("  📄 이메일 템플릿에 사용되는 Django 변수들:")
    for var in template_variables:
        print(f"    - {var}")
    
    print("\n  ✨ 이 변수들은 create_template_context() 메서드에서 자동 생성됩니다.")

if __name__ == "__main__":
    test_dynamic_template_context()
    test_template_variables()