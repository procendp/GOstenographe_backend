# 🛡️ 시스템 리소스 백업 및 복원 가이드

## 📦 백업된 항목

### 1. **관리자 계정** (User)
- 위치: `backups/users_backup.json`
- 개수: 3개
- 용도: Django Admin 로그인 계정

### 2. **이메일 템플릿** (Template)
- 위치: `backups/templates_backup.json`
- 개수: 15개
- 용도: 고객 이메일 발송 템플릿

### 3. **이메일 이미지** (S3)
- 위치: `email_templates/` (S3 버킷)
- 개수: 12개
- 용도: 이메일 내 이미지 리소스
- ⚠️ **절대 삭제 금지!**

---

## 🗑️ 테스트 데이터 삭제

### 사용법:
```bash
./clean_test_data.sh
```

### 삭제 대상:
- ✅ Request (주문 정보)
- ✅ File (파일 메타데이터)
- ✅ SendLog (발송 이력)
- ✅ StatusChangeLog (상태 변경 이력)
- ✅ S3 고객 파일 (root/, transcripts/)

### 유지 대상:
- ✅ User (관리자 계정)
- ✅ Template (이메일 템플릿)
- ✅ S3 email_templates/ (이메일 이미지)

---

## ♻️ 시스템 리소스 복원

### 사용법:
```bash
./restore_system_resources.sh
```

### 복원 항목:
- User (관리자 계정)
- Template (이메일 템플릿)

### 주의사항:
- S3 email_templates는 백업/복원 불필요 (삭제 안 함)
- 복원 전 데이터가 있으면 중복될 수 있음

---

## 🔄 전체 초기화 후 복원 절차

```bash
# 1. 테스트 데이터 삭제
./clean_test_data.sh

# 2. 시스템 리소스 복원
./restore_system_resources.sh

# 3. 확인
python manage.py shell -c "
from core.models import User
from requests.models import Template, Request
print(f'User: {User.objects.count()}개')
print(f'Template: {Template.objects.count()}개')
print(f'Request: {Request.objects.count()}개')
"
```

---

## ⚠️ 주의사항

1. **백업 파일 보호**
   - `backups/*.json` 파일을 Git에 커밋하지 마세요
   - 민감한 정보 (비밀번호 해시) 포함

2. **S3 email_templates**
   - 절대 수동으로 삭제하지 마세요
   - 이메일 발송 시 이미지 깨짐

3. **정기 백업**
   - Template 수정 후 재백업 필요:
     ```bash
     python manage.py dumpdata requests.Template --indent 2 > backups/templates_backup.json
     ```

---

## 📝 재백업 방법

관리자 계정이나 템플릿을 수정했다면:

```bash
# User 재백업
python manage.py dumpdata core.User --indent 2 > backups/users_backup.json

# Template 재백업
python manage.py dumpdata requests.Template --indent 2 > backups/templates_backup.json
```
