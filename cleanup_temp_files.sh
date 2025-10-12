#!/bin/bash

# 임시 파일 자동 정리 스크립트
# Cron으로 매일 실행하여 24시간 이상 경과한 임시 파일 삭제

# 프로젝트 디렉토리로 이동
cd "$(dirname "$0")"

# 가상환경 활성화
source venv/bin/activate

# cleanup 명령 실행
python manage.py cleanup_temp_files --hours=24

# 로그 기록 (선택사항)
echo "[$(date)] 임시 파일 정리 완료" >> logs/cleanup.log

