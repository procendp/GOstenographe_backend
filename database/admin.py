from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from .models import IntegratedView, OrderManagement, RequestManagement
from requests.models import Request

@admin.register(IntegratedView)
class IntegratedViewAdmin(ModelAdmin):
    """통합 관리 - 읽기 전용"""
    list_display = (
        'id', 'name', 'email', 'phone_display', 'status_display',
        'recording_date', 'recording_location', 'speaker_count',
        'draft_format', 'final_option_display', 'created_at'
    )
    list_filter = ('status', 'created_at', 'draft_format', 'final_option', 'speaker_count')
    search_fields = ('name', 'email', 'phone', 'recording_location')
    list_per_page = 25  # 성능 향상을 위해 줄임

    change_list_template = 'admin/excel_database.html'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(is_temporary=False).select_related('transcript_file').prefetch_related('files')

    def phone_display(self, obj):
        """연락처 표시 형식 개선 (010-5590-7193 형태)"""
        if not obj.phone:
            return obj.phone
        
        import re
        # 숫자만 추출
        digits = re.sub(r'\D', '', obj.phone)
        
        # 010으로 시작하는 11자리 번호인 경우
        if len(digits) == 11 and digits.startswith('010'):
            return f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"
        
        # 010으로 시작하는 10자리 번호인 경우 (중간 3자리)
        if len(digits) == 10 and digits.startswith('010'):
            return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
        
        # 다른 형식은 그대로 반환
        return obj.phone
    phone_display.short_description = '연락처'

    def final_option_display(self, obj):
        """최종본 옵션 표시 형식 개선"""
        option_map = {
            'file': '파일',
            'file_post': '파일 + 등기 우편 (+5,000원)',
            'file_post_cd': '파일 + 등기 우편 + CD (+6,000원)',
            'file_post_usb': '파일 + 등기 우편 + USB (+10,000원)'
        }
        return option_map.get(obj.final_option, obj.final_option)
    final_option_display.short_description = '최종본 옵션'

    def status_display(self, obj):
        status_colors = {
            'pending': 'background-color: #fef3c7; color: #92400e; padding: 4px 8px; border-radius: 12px; font-size: 12px;',
            'in_progress': 'background-color: #dbeafe; color: #1e40af; padding: 4px 8px; border-radius: 12px; font-size: 12px;',
            'completed': 'background-color: #dcfce7; color: #166534; padding: 4px 8px; border-radius: 12px; font-size: 12px;',
            'cancelled': 'background-color: #fee2e2; color: #991b1b; padding: 4px 8px; border-radius: 12px; font-size: 12px;'
        }
        style = status_colors.get(obj.status, '')
        return format_html(
            '<span style="{}">{}</span>',
            style,
            obj.get_status_display()
        )
    status_display.short_description = '상태'

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

@admin.register(OrderManagement)
class OrderManagementAdmin(ModelAdmin):
    """Order ID List - Order ID 기준으로 표시"""
    list_display = (
        'order_id_with_requests', 'attachment_files', 'name', 'email', 'phone_display', 'status_display',
        'recording_date', 'speaker_count', 'payment_amount',
        'draft_format', 'final_option_display', 'created_at'
    )
    
    def changelist_view(self, request, extra_context=None):
        """주문서 관리용 커스텀 템플릿 컨텍스트"""
        extra_context = extra_context or {}
        extra_context['hide_request_id'] = True  # Request ID 숨김
        extra_context['show_add_delete'] = True  # 추가/삭제 버튼 표시
        return super().changelist_view(request, extra_context)
    list_filter = ('status', 'created_at', 'draft_format', 'final_option')
    search_fields = ('order_id', 'name', 'email', 'phone')
    list_per_page = 25  # 성능 향상을 위해 줄임
    ordering = ['order_id', '-created_at']
    
    change_list_template = 'admin/excel_database.html'
    
    def final_option_display(self, obj):
        """최종본 옵션 표시 형식 개선"""
        option_map = {
            'file': '파일',
            'file_post': '파일 + 등기 우편 (+5,000원)',
            'file_post_cd': '파일 + 등기 우편 + CD (+6,000원)',
            'file_post_usb': '파일 + 등기 우편 + USB (+10,000원)'
        }
        return option_map.get(obj.final_option, obj.final_option)
    final_option_display.short_description = '최종본 옵션'
    
    def phone_display(self, obj):
        """연락처 표시 형식 개선 (010-5590-7193 형태)"""
        if not obj.phone:
            return obj.phone
        
        import re
        # 숫자만 추출
        digits = re.sub(r'\D', '', obj.phone)
        
        # 010으로 시작하는 11자리 번호인 경우
        if len(digits) == 11 and digits.startswith('010'):
            return f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"
        
        # 010으로 시작하는 10자리 번호인 경우 (중간 3자리)
        if len(digits) == 10 and digits.startswith('010'):
            return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
        
        # 다른 형식은 그대로 반환
        return obj.phone
    phone_display.short_description = '연락처'
    
    def get_queryset(self, request):
        """모든 Request를 표시하되 Order ID로 정렬"""
        qs = super().get_queryset(request)
        # 모든 Request를 표시 (파일별로 행 생성)
        return qs.filter(is_temporary=False).order_by('order_id', 'request_id')
    
    def order_id_with_requests(self, obj):
        """Order ID만 표시 (Request ID는 숨김)"""
        return obj.order_id if obj.order_id else '-'
    order_id_with_requests.short_description = 'Order ID'
    
    def attachment_files(self, obj):
        """첨부 파일 표시"""
        files = obj.files.all()
        if files:
            file_list = []
            for file in files:
                file_name = file.original_name or file.file.split('/')[-1] if file.file else 'Unknown'
                file_size = f"({file.file_size // 1024 // 1024}MB)" if file.file_size else ""
                file_list.append(f"{file_name} {file_size}")
            
            return format_html(
                '<div style="font-size: 12px; color: #374151;">{}</div>',
                '<br>'.join(file_list)
            )
        return format_html('<span style="color: #9ca3af;">No files</span>')
    attachment_files.short_description = '첨부 파일'
    
    def status_display(self, obj):
        status_colors = {
            'received': 'background-color: #fef3c7; color: #92400e;',
            'payment_completed': 'background-color: #dbeafe; color: #1e40af;',
            'in_progress': 'background-color: #e0e7ff; color: #5b21b6;',
            'work_completed': 'background-color: #dcfce7; color: #166534;',
            'sent': 'background-color: #10b981; color: white;',
            'cancelled': 'background-color: #fee2e2; color: #991b1b;'
        }
        style = status_colors.get(obj.status, '')
        return format_html(
            '<span style="{}padding: 4px 8px; border-radius: 12px; font-size: 12px;">{}</span>',
            style, obj.get_status_display()
        )
    status_display.short_description = '상태'

    def has_add_permission(self, request):
        return False  # 커스텀 버튼으로만 추가

    def has_delete_permission(self, request, obj=None):
        return False  # 커스텀 버튼으로만 삭제

    def has_change_permission(self, request, obj=None):
        return False  # 읽기 전용

@admin.register(RequestManagement)
class RequestManagementAdmin(ModelAdmin):
    """Request ID List - Request ID 기준으로 모든 레코드 표시"""
    list_display = (
        'request_id', 'order_id', 'attachment_files', 'name', 'email', 'phone_display', 'status_display',
        'recording_date', 'speaker_count', 'payment_amount',
        'draft_format', 'final_option_display', 'created_at'
    )
    
    def changelist_view(self, request, extra_context=None):
        """Option B용 커스텀 템플릿 컨텍스트"""
        extra_context = extra_context or {}
        extra_context['hide_order_id'] = True  # Option B에서만 Order ID 숨김
        return super().changelist_view(request, extra_context)
        
    list_filter = ('status', 'created_at', 'draft_format', 'final_option')
    search_fields = ('request_id', 'order_id', 'name', 'email', 'phone')
    list_per_page = 25  # 성능 향상을 위해 줄임
    ordering = ['-created_at']
    
    change_list_template = 'admin/excel_database.html'
    
    def get_queryset(self, request):
        """모든 Request ID 표시"""
        qs = super().get_queryset(request)
        return qs.filter(is_temporary=False).select_related('transcript_file').prefetch_related('files')

    def phone_display(self, obj):
        """연락처 표시 형식 개선 (010-5590-7193 형태)"""
        if not obj.phone:
            return obj.phone
        
        import re
        # 숫자만 추출
        digits = re.sub(r'\D', '', obj.phone)
        
        # 010으로 시작하는 11자리 번호인 경우
        if len(digits) == 11 and digits.startswith('010'):
            return f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"
        
        # 010으로 시작하는 10자리 번호인 경우 (중간 3자리)
        if len(digits) == 10 and digits.startswith('010'):
            return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
        
        # 다른 형식은 그대로 반환
        return obj.phone
    phone_display.short_description = '연락처'

    def final_option_display(self, obj):
        """최종본 옵션 표시 형식 개선"""
        option_map = {
            'file': '파일',
            'file_post': '파일 + 등기 우편 (+5,000원)',
            'file_post_cd': '파일 + 등기 우편 + CD (+6,000원)',
            'file_post_usb': '파일 + 등기 우편 + USB (+10,000원)'
        }
        return option_map.get(obj.final_option, obj.final_option)
    final_option_display.short_description = '최종본 옵션'
    
    def attachment_files(self, obj):
        """첨부 파일 표시"""
        files = obj.files.all()
        if files:
            file_list = []
            for file in files:
                file_name = file.original_name or file.file.split('/')[-1] if file.file else 'Unknown'
                file_size = f"({file.file_size // 1024 // 1024}MB)" if file.file_size else ""
                file_list.append(f"{file_name} {file_size}")
            
            return format_html(
                '<div style="font-size: 12px; color: #374151;">{}</div>',
                '<br>'.join(file_list)
            )
        return format_html('<span style="color: #9ca3af;">No files</span>')
    attachment_files.short_description = '첨부 파일'
    
    def status_display(self, obj):
        status_colors = {
            'received': 'background-color: #fef3c7; color: #92400e;',
            'payment_completed': 'background-color: #dbeafe; color: #1e40af;',
            'in_progress': 'background-color: #e0e7ff; color: #5b21b6;',
            'work_completed': 'background-color: #dcfce7; color: #166534;',
            'sent': 'background-color: #10b981; color: white;',
            'cancelled': 'background-color: #fee2e2; color: #991b1b;'
        }
        style = status_colors.get(obj.status, '')
        return format_html(
            '<span style="{}padding: 4px 8px; border-radius: 12px; font-size: 12px;">{}</span>',
            style, obj.get_status_display()
        )
    status_display.short_description = '상태'
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False