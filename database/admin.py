from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from .models import ExcelView, OptionA, OptionB
from requests.models import Request

@admin.register(ExcelView)
class ExcelViewAdmin(ModelAdmin):
    """엑셀 뷰 - 기존과 동일"""
    list_display = (
        'id', 'name', 'email', 'phone', 'status_display', 
        'recording_date', 'recording_location', 'speaker_count',
        'draft_format', 'final_option', 'created_at'
    )
    list_filter = ('status', 'created_at', 'draft_format', 'final_option', 'speaker_count')
    search_fields = ('name', 'email', 'phone', 'recording_location')
    list_per_page = 50
    
    change_list_template = 'admin/excel_database.html'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(is_temporary=False)
    
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

@admin.register(OptionA)
class OptionAAdmin(ModelAdmin):
    """Order ID List - Order ID 기준으로 표시"""
    list_display = (
        'order_id_with_requests', 'file_info', 'name', 'email', 'phone', 'status_display',
        'recording_date', 'speaker_count', 'payment_amount',
        'draft_format', 'final_option', 'created_at'
    )
    
    def changelist_view(self, request, extra_context=None):
        """Option A용 커스텀 템플릿 컨텍스트"""
        extra_context = extra_context or {}
        extra_context['hide_request_id'] = True  # Option A에서만 Request ID 숨김
        return super().changelist_view(request, extra_context)
    list_filter = ('status', 'created_at', 'draft_format', 'final_option')
    search_fields = ('order_id', 'name', 'email', 'phone')
    list_per_page = 50
    ordering = ['order_id', '-created_at']
    
    change_list_template = 'admin/excel_database.html'
    
    def get_queryset(self, request):
        """모든 Request를 표시하되 Order ID로 정렬"""
        qs = super().get_queryset(request)
        # 모든 Request를 표시 (파일별로 행 생성)
        return qs.filter(is_temporary=False).order_by('order_id', 'request_id')
    
    def order_id_with_requests(self, obj):
        """Order ID만 표시 (Request ID는 숨김)"""
        return obj.order_id if obj.order_id else '-'
    order_id_with_requests.short_description = 'Order ID'
    
    def file_info(self, obj):
        """파일 정보 표시 (Request ID는 내부적으로만 사용)"""
        if obj.request_id:
            # 파일 번호를 Order 내에서 계산
            same_order = Request.objects.filter(
                order_id=obj.order_id,
                is_temporary=False
            ).order_by('request_id').values_list('request_id', flat=True)
            
            file_list = list(same_order)
            if obj.request_id in file_list:
                file_num = file_list.index(obj.request_id) + 1
                total_files = len(file_list)
                
                if total_files > 1:
                    return format_html(
                        '<span style="color: #6b7280; font-size: 12px;">File {}/{}</span>',
                        file_num, total_files
                    )
                else:
                    return format_html(
                        '<span style="color: #6b7280; font-size: 12px;">Single file</span>'
                    )
        return '-'
    file_info.short_description = 'File Info'
    
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

@admin.register(OptionB)
class OptionBAdmin(ModelAdmin):
    """Request ID List - Request ID 기준으로 모든 레코드 표시"""
    list_display = (
        'request_id', 'order_id', 'name', 'email', 'phone', 'status_display',
        'recording_date', 'speaker_count', 'payment_amount',
        'draft_format', 'final_option', 'created_at'
    )
    
    def changelist_view(self, request, extra_context=None):
        """Option B용 커스텀 템플릿 컨텍스트"""
        extra_context = extra_context or {}
        extra_context['hide_order_id'] = True  # Option B에서만 Order ID 숨김
        return super().changelist_view(request, extra_context)
        
    list_filter = ('status', 'created_at', 'draft_format', 'final_option')
    search_fields = ('request_id', 'order_id', 'name', 'email', 'phone')
    list_per_page = 50
    ordering = ['-created_at']
    
    change_list_template = 'admin/excel_database.html'
    
    def get_queryset(self, request):
        """모든 Request ID 표시"""
        qs = super().get_queryset(request)
        return qs.filter(is_temporary=False)
    
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