from django.core.management.base import BaseCommand
import os
import re
from pathlib import Path


class Command(BaseCommand):
    help = '템플릿 동기화 상태를 검증합니다'

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🚀 GOstenographe 템플릿 동기화 검증 도구')
        )
        self.stdout.write('=' * 50)
        
        # 템플릿 일관성 검사
        template_ok = self.check_template_consistency()
        
        # Admin 설정 동기화 검사
        self.check_admin_sync()
        
        self.stdout.write('=' * 50)
        if template_ok:
            self.stdout.write(
                self.style.SUCCESS('🎉 모든 검증이 완료되었습니다!')
            )
        else:
            self.stdout.write(
                self.style.ERROR('💥 검증 실패! 위의 수정 사항을 확인해주세요.')
            )

    def check_template_consistency(self):
        """템플릿 일관성을 검증합니다."""
        
        # 템플릿 파일 경로
        template_path = Path(__file__).parent.parent.parent.parent / "templates" / "admin" / "excel_database.html"
        
        if not template_path.exists():
            self.stdout.write(
                self.style.ERROR(f"❌ 템플릿 파일을 찾을 수 없습니다: {template_path}")
            )
            return False
        
        self.stdout.write("🔍 템플릿 일관성 검증 중...")
        self.stdout.write(f"📁 파일: {template_path}")
        
        # 템플릿 내용 읽기
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 컬럼 헤더 개수 계산
        header_count = self.count_column_headers(content)
        
        # colspan 값 추출
        colspan_value = self.extract_colspan_value(content)
        
        # 결과 출력
        self.stdout.write(f"📊 컬럼 헤더 개수: {header_count}")
        self.stdout.write(f"📊 colspan 값: {colspan_value}")
        
        # 일관성 검사
        is_consistent = header_count == colspan_value
        
        if is_consistent:
            self.stdout.write(
                self.style.SUCCESS("✅ 템플릿 일관성 검증 통과!")
            )
            self.stdout.write("   컬럼 헤더 개수와 colspan 값이 일치합니다.")
        else:
            self.stdout.write(
                self.style.ERROR("❌ 템플릿 일관성 검증 실패!")
            )
            self.stdout.write(f"   컬럼 헤더 개수: {header_count}")
            self.stdout.write(f"   colspan 값: {colspan_value}")
            self.stdout.write("   두 값이 일치하지 않습니다.")
            self.stdout.write("\n🛠️ 수정 방법:")
            self.stdout.write(f"   템플릿에서 colspan=\"{colspan_value}\"을 colspan=\"{header_count}\"로 변경하세요.")
        
        return is_consistent

    def count_column_headers(self, content):
        """컬럼 헤더 개수를 계산합니다."""
        
        # <thead> 태그 내의 <th> 태그 개수 계산
        thead_pattern = r'<thead[^>]*>(.*?)</thead>'
        thead_match = re.search(thead_pattern, content, re.DOTALL)
        
        if not thead_match:
            self.stdout.write("⚠️ <thead> 태그를 찾을 수 없습니다.")
            return 0
        
        thead_content = thead_match.group(1)
        
        # <th> 태그 개수 계산 (resizable-th 클래스가 있는 것만)
        th_tags = re.findall(r'<th[^>]*class="[^"]*resizable-th[^"]*"[^>]*>', thead_content)
        
        # 체크박스 컬럼도 포함 (resizable-th 클래스가 없는 <th>도 있음)
        all_th_tags = re.findall(r'<th[^>]*>', thead_content)
        
        self.stdout.write(f"   상세: resizable-th 컬럼 {len(th_tags)}개, 전체 <th> 태그 {len(all_th_tags)}개")
        
        return len(all_th_tags)

    def extract_colspan_value(self, content):
        """colspan 값을 추출합니다."""
        
        # colspan="숫자" 패턴 찾기
        colspan_pattern = r'colspan="(\d+)"'
        match = re.search(colspan_pattern, content)
        
        if match:
            return int(match.group(1))
        else:
            self.stdout.write("⚠️ colspan 값을 찾을 수 없습니다.")
            return 0

    def check_admin_sync(self):
        """Admin 설정과의 동기화를 확인합니다."""
        
        self.stdout.write("\n🔍 Admin 설정 동기화 확인 중...")
        
        # admin.py 파일들에서 list_display 확인
        admin_files = [
            Path(__file__).parent.parent.parent.parent / "database" / "admin.py",
            Path(__file__).parent.parent.parent.parent / "requests" / "admin.py"
        ]
        
        for admin_file in admin_files:
            if admin_file.exists():
                self.stdout.write(f"📁 {admin_file.name} 확인 중...")
                self.check_admin_file(admin_file)

    def check_admin_file(self, admin_file):
        """개별 admin 파일의 list_display를 확인합니다."""
        
        with open(admin_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # list_display에서 recording_location과 estimated_price 확인
        has_recording_location = 'recording_location' in content
        has_estimated_price = 'estimated_price' in content
        
        status_style = self.style.SUCCESS if has_recording_location else self.style.ERROR
        self.stdout.write(f"   recording_location: {status_style('✅' if has_recording_location else '❌')}")
        
        status_style = self.style.SUCCESS if has_estimated_price else self.style.ERROR
        self.stdout.write(f"   estimated_price: {status_style('✅' if has_estimated_price else '❌')}")
        
        if not has_recording_location or not has_estimated_price:
            self.stdout.write(
                self.style.WARNING(f"   ⚠️ {admin_file.name}에서 필요한 필드가 누락되었습니다.")
            )
