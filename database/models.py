from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from requests.models import Request

# Database 섹션에 나타날 프록시 모델들
class IntegratedView(Request):
    """통합 관리 - 전체 데이터 통합 조회"""

    class Meta:
        proxy = True
        verbose_name = _('1. 통합 관리')
        verbose_name_plural = _('1. 통합 관리')
        app_label = 'database'

    def __str__(self):
        return f"{self.name} - {self.get_status_display()}"

    def final_option_display(self):
        """최종본 옵션을 사용자 친화적 텍스트로 표시"""
        option_map = {
            'file': '파일',
            'file_post': '파일 +등기 우편 (+5,000원)',
            'file_post_cd': '파일 +등기 우편 +CD (+6,000원)',
            'file_post_usb': '파일 +등기 우편 +USB (+10,000원)',
            'file_usb': '파일+우편 (+5,000원)',  # 기존 값 호환성
            'file_usb_cd': '파일+우편+CD (+5,000원)',  # 기존 값 호환성
            'file_usb_post': '파일+우편+USB (+5,000원)',  # 기존 값 호환성
        }
        return option_map.get(self.final_option, self.final_option)
    final_option_display.short_description = '최종본 옵션'

    def phone_display(self):
        """연락처를 하이픈 포함 형식으로 표시"""
        if not self.phone:
            return '-'
        
        # 숫자만 추출
        phone_digits = ''.join(filter(str.isdigit, self.phone))
        
        # 010으로 시작하는 11자리 번호인 경우
        if len(phone_digits) == 11 and phone_digits.startswith('010'):
            return f"{phone_digits[:3]}-{phone_digits[3:7]}-{phone_digits[7:]}"
        # 02로 시작하는 10자리 번호인 경우 (서울)
        elif len(phone_digits) == 10 and phone_digits.startswith('02'):
            return f"{phone_digits[:2]}-{phone_digits[2:6]}-{phone_digits[6:]}"
        # 기타 지역번호로 시작하는 10자리 번호인 경우
        elif len(phone_digits) == 10:
            return f"{phone_digits[:3]}-{phone_digits[3:6]}-{phone_digits[6:]}"
        # 형식이 맞지 않는 경우 원본 반환
        else:
            return self.phone
    phone_display.short_description = '연락처'

class OrderManagement(Request):
    """주문서 관리 - Order ID 기준 추가/삭제 및 결제 관리"""

    class Meta:
        proxy = True
        verbose_name = _('2. 주문서 관리 (추가/삭제, 결제 처리)')
        verbose_name_plural = _('2. 주문서 관리 (추가/삭제, 결제 처리)')
        app_label = 'database'

    def __str__(self):
        return f"[{self.order_id}] {self.name}"

    def final_option_display(self):
        """최종본 옵션을 사용자 친화적 텍스트로 표시"""
        option_map = {
            'file': '파일',
            'file_post': '파일 +등기 우편 (+5,000원)',
            'file_post_cd': '파일 +등기 우편 +CD (+6,000원)',
            'file_post_usb': '파일 +등기 우편 +USB (+10,000원)',
            'file_usb': '파일+우편 (+5,000원)',  # 기존 값 호환성
            'file_usb_cd': '파일+우편+CD (+5,000원)',  # 기존 값 호환성
            'file_usb_post': '파일+우편+USB (+5,000원)',  # 기존 값 호환성
        }
        return option_map.get(self.final_option, self.final_option)
    final_option_display.short_description = '최종본 옵션'

    def phone_display(self):
        """연락처를 하이픈 포함 형식으로 표시"""
        if not self.phone:
            return '-'
        
        # 숫자만 추출
        phone_digits = ''.join(filter(str.isdigit, self.phone))
        
        # 010으로 시작하는 11자리 번호인 경우
        if len(phone_digits) == 11 and phone_digits.startswith('010'):
            return f"{phone_digits[:3]}-{phone_digits[3:7]}-{phone_digits[7:]}"
        # 02로 시작하는 10자리 번호인 경우 (서울)
        elif len(phone_digits) == 10 and phone_digits.startswith('02'):
            return f"{phone_digits[:2]}-{phone_digits[2:6]}-{phone_digits[6:]}"
        # 기타 지역번호로 시작하는 10자리 번호인 경우
        elif len(phone_digits) == 10:
            return f"{phone_digits[:3]}-{phone_digits[3:6]}-{phone_digits[6:]}"
        # 형식이 맞지 않는 경우 원본 반환
        else:
            return self.phone
    phone_display.short_description = '연락처'

class RequestManagement(Request):
    """요청서 관리 - Request ID 기준 파일 및 작업 관리"""

    class Meta:
        proxy = True
        verbose_name = _('3. 요청서 관리 (파일/작업)')
        verbose_name_plural = _('3. 요청서 관리 (파일/작업)')
        app_label = 'database'

    def __str__(self):
        return f"[{self.request_id}] {self.name}"

    def final_option_display(self):
        """최종본 옵션을 사용자 친화적 텍스트로 표시"""
        option_map = {
            'file': '파일',
            'file_post': '파일 +등기 우편 (+5,000원)',
            'file_post_cd': '파일 +등기 우편 +CD (+6,000원)',
            'file_post_usb': '파일 +등기 우편 +USB (+10,000원)',
            'file_usb': '파일+우편 (+5,000원)',  # 기존 값 호환성
            'file_usb_cd': '파일+우편+CD (+5,000원)',  # 기존 값 호환성
            'file_usb_post': '파일+우편+USB (+5,000원)',  # 기존 값 호환성
        }
        return option_map.get(self.final_option, self.final_option)
    final_option_display.short_description = '최종본 옵션'

    def phone_display(self):
        """연락처를 하이픈 포함 형식으로 표시"""
        if not self.phone:
            return '-'
        
        # 숫자만 추출
        phone_digits = ''.join(filter(str.isdigit, self.phone))
        
        # 010으로 시작하는 11자리 번호인 경우
        if len(phone_digits) == 11 and phone_digits.startswith('010'):
            return f"{phone_digits[:3]}-{phone_digits[3:7]}-{phone_digits[7:]}"
        # 02로 시작하는 10자리 번호인 경우 (서울)
        elif len(phone_digits) == 10 and phone_digits.startswith('02'):
            return f"{phone_digits[:2]}-{phone_digits[2:6]}-{phone_digits[6:]}"
        # 기타 지역번호로 시작하는 10자리 번호인 경우
        elif len(phone_digits) == 10:
            return f"{phone_digits[:3]}-{phone_digits[3:6]}-{phone_digits[6:]}"
        # 형식이 맞지 않는 경우 원본 반환
        else:
            return self.phone
    phone_display.short_description = '연락처'

# 하위 호환성을 위한 별칭 (기존 코드에서 사용 중일 수 있음)
ExcelView = IntegratedView
OptionA = OrderManagement
OptionB = RequestManagement
