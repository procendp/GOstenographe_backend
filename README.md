# GOstenographe_backend

## 임시 파일 자동 정리

### Management Command

24시간 이상 경과한 임시 파일 및 Request를 자동으로 삭제합니다.

```bash
# 테스트 (실제 삭제 안함)
python manage.py cleanup_temp_files --dry-run

# 실제 실행 (기본: 24시간)
python manage.py cleanup_temp_files

# 시간 커스텀 (예: 48시간)
python manage.py cleanup_temp_files --hours=48
```

### Cron 설정

매일 새벽 3시에 자동 실행:

```bash
# crontab 편집
crontab -e

# 아래 내용 추가
0 3 * * * /Users/jamoo/Project/GOstenographeWebProject/GOstenographe_backend/cleanup_temp_files.sh
```

또는 스크립트 직접 실행:

```bash
./cleanup_temp_files.sh
```

### 동작 방식

1. **GNB 클릭**: 커스텀 모달로 파일 삭제 확인 후 이동
2. **beforeunload**: 브라우저 경고 (뒤로가기/새로고침/닫기)
3. **자동 정리**: 24시간 경과한 임시 파일 자동 삭제 (Cron)