from django.db import models
from django.utils.translation import gettext_lazy as _
from requests.models import Request

# Database 섹션에 나타날 프록시 모델들
class ExcelView(Request):
    """엑셀 뷰 - 기존과 동일"""
    
    class Meta:
        proxy = True
        verbose_name = _('엑셀 뷰')
        verbose_name_plural = _('엑셀 뷰')
        app_label = 'database'
        
    def __str__(self):
        return f"{self.name} - {self.get_status_display()}"

class OptionA(Request):
    """Order ID List - Order ID 기준 표시"""
    
    class Meta:
        proxy = True
        verbose_name = _('Order ID List')
        verbose_name_plural = _('Order ID List')
        app_label = 'database'
        
    def __str__(self):
        return f"[{self.order_id}] {self.name}"

class OptionB(Request):
    """Request ID List - Request ID 기준 표시"""
    
    class Meta:
        proxy = True
        verbose_name = _('Request ID List')
        verbose_name_plural = _('Request ID List')
        app_label = 'database'
        
    def __str__(self):
        return f"[{self.request_id}] {self.name}"
