# NCP SMS 설정 가이드

## 📋 목차
1. [NCP SMS 서비스 신청](#1-ncp-sms-서비스-신청)
2. [API 인증 정보 생성](#2-api-인증-정보-생성)
3. [발신번호 등록](#3-발신번호-등록)
4. [Django 설정](#4-django-설정)
5. [템플릿 생성](#5-템플릿-생성)
6. [SMS 발송 테스트](#6-sms-발송-테스트)
7. [문제 해결](#7-문제-해결)

---

## 1. NCP SMS 서비스 신청

### 1-1. NCP 콘솔 접속
1. https://console.ncloud.com/ 접속
2. 네이버 클라우드 플랫폼 로그인

### 1-2. SMS 서비스 활성화
1. 좌측 메뉴에서 **Services** → **Application Service** → **Simple & Easy Notification Service**  클릭
2. **이용 신청하기** 버튼 클릭
3. 이용 약관 동의 후 신청 완료

---

## 2. API 인증 정보 생성

### 2-1. Access Key & Secret Key 발급

1. **마이페이지** → **계정 관리** → **인증키 관리** 이동
2. **신규 API 인증키 생성** 클릭
3. 생성된 정보 확인:
   - **Access Key ID**: `NAVER_ACCESS_KEY`로 사용
   - **Secret Key**: `NAVER_SECRET_KEY`로 사용
   - ⚠️ **Secret Key는 생성 시 한 번만 표시되므로 반드시 저장하세요!**

### 2-2. Service ID 확인

1. **Services** → **Simple & Easy Notification Service** → **프로젝트** 선택
2. 프로젝트 상세 페이지에서 **Service ID** 확인
   - 형식: `ncp:sms:kr:xxxxx:xxxxxx`
   - 이 값을 `NAVER_SERVICE_ID`로 사용

---

## 3. 발신번호 등록

### 3-1. 발신번호 등록 신청
1. **SMS** → **발신번호** 메뉴 이동
2. **발신번호 등록** 버튼 클릭
3. 발신번호 입력: **010-2681-2571** (속기사무소 정 대표번호)
4. 인증 방법 선택:
   - **서류 인증**: 사업자등록증 업로드
   - **SMS 인증**: 해당 번호로 인증번호 수신

### 3-2. 등록 완료 대기
- 승인까지 영업일 기준 1~2일 소요
- 승인 완료 시 이메일 또는 SMS로 알림 발송
- 승인 전에는 SMS 발송 불가

---

## 4. Django 설정

### 4-1. 환경 변수 설정

`GOstenographe_backend/.env` 파일에 다음 내용 추가:

```env
# Naver Cloud SMS Settings
NAVER_ACCESS_KEY=발급받은_Access_Key_ID
NAVER_SECRET_KEY=발급받은_Secret_Key
NAVER_SERVICE_ID=확인한_Service_ID
SENDER_PHONE=01026812571
```

⚠️ **주의사항:**
- `SENDER_PHONE`은 하이픈(-) 없이 숫자만 입력
- 반드시 등록되고 승인된 발신번호만 사용 가능
- `.env` 파일은 `.gitignore`에 포함되어 있어 Git에 커밋되지 않습니다

### 4-2. 설정 확인

```python
# config/settings.py에 이미 설정되어 있음
NAVER_ACCESS_KEY = os.getenv('NAVER_ACCESS_KEY', '')
NAVER_SECRET_KEY = os.getenv('NAVER_SECRET_KEY', '')
NAVER_SERVICE_ID = os.getenv('NAVER_SERVICE_ID', '')
SENDER_PHONE = os.getenv('SENDER_PHONE', '')
```

---

## 5. 템플릿 생성

### 5-1. SMS 템플릿 생성 스크립트 실행

배포 환경 (Render)에서 실행:

```bash
cd GOstenographe_backend
python manage.py shell < create_sms_templates.py
```

### 5-2. 생성되는 템플릿 (4개)

| 템플릿명 | 용도 | 글자 수 | 타입 |
|---------|------|---------|------|
| `quotation_sent_sms` | 입금 안내 (견적 발송) | ~800자 | LMS |
| `payment_completed_sms` | 입금 확인 (결제 완료) | ~100자 | LMS |
| `draft_sent_sms` | 초안/수정안 발송 안내 | ~80자 | SMS |
| `final_sent_sms` | 최종안 발송 안내 | ~80자 | SMS |

### 5-3. SMS vs LMS 구분

- **SMS**: 90자 이하 (한글 기준 ~80자)
  - 가격: 건당 약 9원
  - 용도: 짧은 알림

- **LMS** (Long Message Service): 91자 이상, 최대 2,000자
  - 가격: 건당 약 30원
  - 용도: 긴 내용의 안내 (입금 안내 등)
  - 제목 포함 가능

**자동 선택**: `sms_sender.py`의 `send_sms()` 함수가 글자 수에 따라 자동으로 SMS/LMS 선택

---

## 6. SMS 발송 테스트

### 6-1. Django Shell에서 직접 테스트

```python
# Render 배포 환경에서 실행
python manage.py shell

# Shell에서 실행
from notification_service.sms_sender import NaverCloudSMS
from requests.models import Request

# SMS 발송 객체 생성
sms = NaverCloudSMS()

# 테스트 발송 (본인 번호로)
sms.send_sms(
    to='01012345678',  # 받을 번호
    content='[테스트] 속기사무소 정 SMS 테스트입니다.'
)

# 템플릿 사용 테스트
from notification_service.template_engine import TemplateEngine
from requests.models import Template

# 템플릿 가져오기
template = Template.objects.get(name='payment_completed_sms')

# Request 객체 가져오기 (실제 데이터 사용)
request = Request.objects.filter(is_temporary=False).first()

# 템플릿 렌더링
engine = TemplateEngine()
message = engine.replace_variables(template.content, request)

# 발송
sms.send_sms(
    to=request.phone,  # Request의 전화번호로
    content=message
)
```

### 6-2. 관리 명령어로 테스트

```bash
# notification_service/test_sms.py 스크립트 사용
cd GOstenographe_backend
python manage.py shell < test_sms.py
```

---

## 7. SMS 발송 활성화

### 7-1. 알림 규칙 설정

`notification_service/notification_service.py` 파일에서 SMS 활성화:

```python
# 196-208줄
notification_rules = {
    'quotation_sent': {'sms': True, 'email': True},      # 입금 안내
    'payment_completed': {'sms': True, 'email': True},   # 입금 확인
    'draft_sent': {'sms': True, 'email': True},          # 초안 발송
    'final_sent': {'sms': True, 'email': True},          # 최종안 발송
}
```

⚠️ **주의:**
- 현재는 모두 `False`로 설정되어 있음
- 테스트 완료 후 필요한 알림만 `True`로 변경
- SMS 비용이 발생하므로 신중하게 활성화

### 7-2. 선택적 활성화 권장

비용 절감을 위해 중요한 알림만 SMS 활성화:

```python
notification_rules = {
    'quotation_sent': {'sms': True, 'email': True},      # 입금 안내는 SMS + Email
    'payment_completed': {'sms': True, 'email': True},   # 입금 확인도 SMS + Email
    'draft_sent': {'sms': False, 'email': True},         # 초안은 Email만
    'final_sent': {'sms': False, 'email': True},         # 최종안도 Email만
}
```

---

## 8. 문제 해결

### 8-1. 발송 실패 원인

| 오류 | 원인 | 해결 방법 |
|------|------|-----------|
| `401 Unauthorized` | 인증 정보 오류 | Access Key, Secret Key 재확인 |
| `403 Forbidden` | 발신번호 미등록 | 발신번호 등록 및 승인 대기 |
| `404 Not Found` | Service ID 오류 | Service ID 재확인 |
| `400 Bad Request` | 메시지 형식 오류 | 전화번호 형식, 메시지 길이 확인 |

### 8-2. 로그 확인

```python
# Django Shell에서 SendLog 확인
from requests.models import SendLog

# 최근 SMS 발송 로그 조회
logs = SendLog.objects.filter(send_type='sms').order_by('-sent_at')[:10]

for log in logs:
    print(f"발송일시: {log.sent_at}")
    print(f"수신자: {log.recipient}")
    print(f"성공여부: {log.success}")
    if not log.success:
        print(f"오류: {log.error_message}")
    print("-" * 50)
```

### 8-3. 테스트 팁

1. **본인 번호로 먼저 테스트**: 고객에게 발송 전 반드시 본인 번호로 테스트
2. **템플릿 변수 확인**: `{name}`, `{estimated_price}` 등이 제대로 치환되는지 확인
3. **글자 수 확인**: LMS로 전환되는 템플릿의 경우 2,000자 제한 주의
4. **비용 모니터링**: NCP 콘솔에서 SMS 사용량 및 비용 확인

---

## 9. 비용 안내

### 9-1. NCP SMS 요금 (2024년 기준)

- **SMS** (90자 이하): 건당 9원
- **LMS** (91~2,000자): 건당 30원
- **부가세**: 별도 10%

### 9-2. 월 예상 비용 계산

예시: 하루 10건 주문 가정

```
하루 10건 × 30일 = 300건/월

시나리오 1 (모든 알림 SMS 활성화):
- 입금 안내 (LMS): 300건 × 30원 = 9,000원
- 입금 확인 (LMS): 300건 × 30원 = 9,000원
- 초안 발송 (SMS): 300건 × 9원 = 2,700원
- 최종안 발송 (SMS): 300건 × 9원 = 2,700원
= 월 23,400원 + VAT

시나리오 2 (중요 알림만 SMS):
- 입금 안내 (LMS): 300건 × 30원 = 9,000원
- 입금 확인 (LMS): 300건 × 30원 = 9,000원
= 월 18,000원 + VAT
```

---

## 10. 체크리스트

SMS 발송 전 확인사항:

- [ ] NCP SMS 서비스 신청 완료
- [ ] Access Key, Secret Key 발급 완료
- [ ] Service ID 확인 완료
- [ ] 발신번호 등록 및 승인 완료
- [ ] `.env` 파일에 인증 정보 입력 완료
- [ ] SMS 템플릿 4개 생성 완료
- [ ] 본인 번호로 테스트 발송 성공
- [ ] 템플릿 변수 치환 정상 작동 확인
- [ ] 알림 규칙에서 필요한 SMS만 활성화
- [ ] SendLog에서 발송 로그 정상 기록 확인

---

## 📞 문의

설정 중 문제가 발생하면 NCP 고객센터로 문의:
- 전화: 1544-0876
- 이메일: 1:1 문의 (NCP 콘솔)
- 문서: https://guide.ncloud-docs.com/docs/sens-overview
