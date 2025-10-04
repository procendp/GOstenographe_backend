#!/bin/bash
# 시스템 리소스 복원 스크립트
# 사용법: ./restore_system_resources.sh

echo "=== 시스템 리소스 복원 시작 ==="

# 가상환경 활성화
source venv/bin/activate

# User 복원
echo "1. 관리자 계정 복원 중..."
python manage.py loaddata backups/users_backup.json
echo "✅ User 복원 완료"

# Template 복원
echo "2. 이메일 템플릿 복원 중..."
python manage.py loaddata backups/templates_backup.json
echo "✅ Template 복원 완료"

echo ""
echo "=== 복원 완료 ==="
echo "복원된 항목:"
echo "  - User (관리자 계정)"
echo "  - Template (이메일 템플릿)"
echo ""
echo "⚠️  S3의 email_templates/는 그대로 유지됩니다."
