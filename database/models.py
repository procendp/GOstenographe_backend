from django.db import models
from django.utils.translation import gettext_lazy as _
from requests.models import Request

# Database 섹션에 나타날 프록시 모델들
class IntegratedView(Request):
    """통합 뷰 - 전체 데이터 통합 조회"""

    class Meta:
        proxy = True
        verbose_name = _('1. 통합 뷰')
        verbose_name_plural = _('1. 통합 뷰')
        app_label = 'database'

    def __str__(self):
        return f"{self.name} - {self.get_status_display()}"

class OrderManagement(Request):
    """주문서 관리 - Order ID 기준 결제 및 주문 관리"""

    class Meta:
        proxy = True
        verbose_name = _('2. 주문서 관리 (결제)')
        verbose_name_plural = _('2. 주문서 관리 (결제)')
        app_label = 'database'

    def __str__(self):
        return f"[{self.order_id}] {self.name}"

class RequestManagement(Request):
    """요청서 관리 - Request ID 기준 파일 및 작업 관리"""

    class Meta:
        proxy = True
        verbose_name = _('3. 요청서 관리 (파일/작업)')
        verbose_name_plural = _('3. 요청서 관리 (파일/작업)')
        app_label = 'database'

    def __str__(self):
        return f"[{self.request_id}] {self.name}"

# 하위 호환성을 위한 별칭 (기존 코드에서 사용 중일 수 있음)
ExcelView = IntegratedView
OptionA = OrderManagement
OptionB = RequestManagement
