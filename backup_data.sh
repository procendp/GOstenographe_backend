#!/usr/bin/env bash
# 데이터베이스 백업 스크립트

# 날짜 형식
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="backups"

# 백업 디렉토리 생성
mkdir -p $BACKUP_DIR

echo "=== 데이터베이스 백업 시작 ==="
echo "시간: $DATE"

# Django 전체 데이터 백업 (JSON)
echo "1. 전체 데이터 백업 중..."
python manage.py dumpdata --natural-foreign --natural-primary \
  --exclude contenttypes --exclude auth.permission \
  --indent 2 > $BACKUP_DIR/full_backup_$DATE.json

if [ $? -eq 0 ]; then
    echo "✓ 전체 데이터 백업 완료: $BACKUP_DIR/full_backup_$DATE.json"
else
    echo "✗ 전체 데이터 백업 실패"
    exit 1
fi

# 중요 앱별 백업
echo "2. 사용자 데이터 백업 중..."
python manage.py dumpdata core \
  --natural-foreign --natural-primary \
  --indent 2 > $BACKUP_DIR/users_backup_$DATE.json

echo "3. 요청 데이터 백업 중..."
python manage.py dumpdata requests \
  --natural-foreign --natural-primary \
  --indent 2 > $BACKUP_DIR/requests_backup_$DATE.json

# 백업 파일 크기 확인
echo ""
echo "=== 백업 완료 ==="
echo "백업 파일:"
ls -lh $BACKUP_DIR/*_$DATE.json

# 오래된 백업 파일 삭제 (30일 이상)
echo ""
echo "=== 오래된 백업 파일 정리 ==="
find $BACKUP_DIR -name "*.json" -mtime +30 -delete
echo "30일 이상 된 백업 파일 삭제 완료"

echo ""
echo "=== 모든 백업 작업 완료 ==="

