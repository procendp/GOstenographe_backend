#!/usr/bin/env python3
"""
템플릿 일관성 검증 스크립트
excel_database.html 템플릿의 컬럼 수와 colspan 값이 일치하는지 확인
"""

import re
import os
from pathlib import Path

def check_template_consistency():
    """템플릿 일관성을 검증합니다."""
    
    # 템플릿 파일 경로
    template_path = Path(__file__).parent / "templates" / "admin" / "excel_database.html"
    
    if not template_path.exists():
        print("❌ 템플릿 파일을 찾을 수 없습니다:", template_path)
        return False
    
    print("🔍 템플릿 일관성 검증 중...")
    print(f"📁 파일: {template_path}")
    
    # 템플릿 내용 읽기
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 컬럼 헤더 개수 계산
    header_count = count_column_headers(content)
    
    # colspan 값 추출
    colspan_value = extract_colspan_value(content)
    
    # 결과 출력
    print(f"📊 컬럼 헤더 개수: {header_count}")
    print(f"📊 colspan 값: {colspan_value}")
    
    # 일관성 검사
    is_consistent = header_count == colspan_value
    
    if is_consistent:
        print("✅ 템플릿 일관성 검증 통과!")
        print("   컬럼 헤더 개수와 colspan 값이 일치합니다.")
    else:
        print("❌ 템플릿 일관성 검증 실패!")
        print(f"   컬럼 헤더 개수: {header_count}")
        print(f"   colspan 값: {colspan_value}")
        print("   두 값이 일치하지 않습니다.")
        print("\n🛠️ 수정 방법:")
        print(f"   템플릿의 762번 라인에서 colspan=\"{colspan_value}\"을 colspan=\"{header_count}\"로 변경하세요.")
    
    return is_consistent

def count_column_headers(content):
    """컬럼 헤더 개수를 계산합니다."""
    
    # <thead> 태그 내의 <th> 태그 개수 계산
    thead_pattern = r'<thead[^>]*>(.*?)</thead>'
    thead_match = re.search(thead_pattern, content, re.DOTALL)
    
    if not thead_match:
        print("⚠️ <thead> 태그를 찾을 수 없습니다.")
        return 0
    
    thead_content = thead_match.group(1)
    
    # <th> 태그 개수 계산 (resizable-th 클래스가 있는 것만)
    th_tags = re.findall(r'<th[^>]*class="[^"]*resizable-th[^"]*"[^>]*>', thead_content)
    
    # 체크박스 컬럼도 포함 (resizable-th 클래스가 없는 <th>도 있음)
    all_th_tags = re.findall(r'<th[^>]*>', thead_content)
    
    print(f"   상세: resizable-th 컬럼 {len(th_tags)}개, 전체 <th> 태그 {len(all_th_tags)}개")
    
    return len(all_th_tags)

def extract_colspan_value(content):
    """colspan 값을 추출합니다."""
    
    # colspan="숫자" 패턴 찾기
    colspan_pattern = r'colspan="(\d+)"'
    match = re.search(colspan_pattern, content)
    
    if match:
        return int(match.group(1))
    else:
        print("⚠️ colspan 값을 찾을 수 없습니다.")
        return 0

def check_admin_sync():
    """Admin 설정과의 동기화를 확인합니다."""
    
    print("\n🔍 Admin 설정 동기화 확인 중...")
    
    # admin.py 파일들에서 list_display 확인
    admin_files = [
        Path(__file__).parent / "database" / "admin.py",
        Path(__file__).parent / "requests" / "admin.py"
    ]
    
    for admin_file in admin_files:
        if admin_file.exists():
            print(f"📁 {admin_file.name} 확인 중...")
            check_admin_file(admin_file)

def check_admin_file(admin_file):
    """개별 admin 파일의 list_display를 확인합니다."""
    
    with open(admin_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # list_display에서 recording_location과 estimated_price 확인
    has_recording_location = 'recording_location' in content
    has_estimated_price = 'estimated_price' in content
    
    print(f"   recording_location: {'✅' if has_recording_location else '❌'}")
    print(f"   estimated_price: {'✅' if has_estimated_price else '❌'}")
    
    if not has_recording_location or not has_estimated_price:
        print(f"   ⚠️ {admin_file.name}에서 필요한 필드가 누락되었습니다.")

if __name__ == "__main__":
    print("🚀 GOstenographe 템플릿 일관성 검증 도구")
    print("=" * 50)
    
    # 템플릿 일관성 검사
    template_ok = check_template_consistency()
    
    # Admin 설정 동기화 검사
    check_admin_sync()
    
    print("\n" + "=" * 50)
    if template_ok:
        print("🎉 모든 검증이 완료되었습니다!")
        exit(0)
    else:
        print("💥 검증 실패! 위의 수정 사항을 확인해주세요.")
        exit(1)
