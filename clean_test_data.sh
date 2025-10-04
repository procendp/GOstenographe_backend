#!/bin/bash
# 테스트 데이터 전체 삭제 스크립트
# 사용법: ./clean_test_data.sh

echo "=== 테스트 데이터 삭제 시작 ==="
echo ""
echo "⚠️  다음 항목이 삭제됩니다:"
echo "  [DB]"
echo "    - Request (37개)"
echo "    - File (30개)"
echo "    - SendLog (22개)"
echo "    - StatusChangeLog (53개)"
echo ""
echo "  [S3]"
echo "    - root/* (고객 파일 32개)"
echo "    - transcripts/* (속기록 1개)"
echo ""
echo "✅ 다음 항목은 유지됩니다:"
echo "  [DB]"
echo "    - User (관리자 계정)"
echo "    - Template (이메일 템플릿)"
echo ""
echo "  [S3]"
echo "    - email_templates/* (이메일 이미지 12개)"
echo ""
read -p "계속하시겠습니까? (y/N): " confirm

if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
    echo "취소되었습니다."
    exit 1
fi

# 가상환경 활성화
source venv/bin/activate

echo ""
echo "1. DB 데이터 삭제 중..."

# Django shell로 데이터 삭제
python manage.py shell << EOF
from requests.models import Request, File, SendLog, StatusChangeLog

# 삭제 전 개수 확인
request_count = Request.objects.count()
file_count = File.objects.count()
sendlog_count = SendLog.objects.count()
statuslog_count = StatusChangeLog.objects.count()

print(f'삭제 예정: Request {request_count}개, File {file_count}개, SendLog {sendlog_count}개, StatusChangeLog {statuslog_count}개')

# 삭제 실행 (CASCADE로 연관 데이터도 자동 삭제)
Request.objects.all().delete()
File.objects.all().delete()
SendLog.objects.all().delete()
StatusChangeLog.objects.all().delete()

print('✅ DB 데이터 삭제 완료')
EOF

echo ""
echo "2. S3 파일 삭제 중..."

# S3 파일 삭제 (email_templates 제외)
python << 'PYEOF'
import boto3
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings

s3_client = boto3.client(
    's3',
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    region_name=settings.AWS_S3_REGION_NAME
)

bucket = settings.AWS_STORAGE_BUCKET_NAME
response = s3_client.list_objects_v2(Bucket=bucket)

if 'Contents' in response:
    deleted_count = 0
    for obj in response['Contents']:
        key = obj['Key']

        # email_templates는 제외
        if not key.startswith('email_templates/'):
            s3_client.delete_object(Bucket=bucket, Key=key)
            deleted_count += 1
            print(f'삭제: {key}')

    print(f'\n✅ S3 파일 {deleted_count}개 삭제 완료')
else:
    print('S3에 삭제할 파일이 없습니다.')
PYEOF

echo ""
echo "=== 삭제 완료 ==="
echo ""
echo "현재 상태:"
echo "  [DB] User, Template만 남음"
echo "  [S3] email_templates만 남음"
echo ""
echo "복원이 필요하면: ./restore_system_resources.sh"
