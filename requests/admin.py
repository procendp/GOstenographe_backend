from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.conf import settings
from .models import Request, Template, SendLog, File, ExcelDatabase
from django.utils import timezone
from datetime import datetime, time
import boto3
import os
from unfold.admin import ModelAdmin

class FileInline(admin.TabularInline):
    model = File
    extra = 0
    fields = ('file_link', 'original_name', 'created_at')
    readonly_fields = ('file_link', 'original_name', 'created_at')
    can_delete = False

    def file_link(self, obj):
        print(f'[ADMIN file_link] obj.id={getattr(obj, "id", None)}, original_name={getattr(obj, "original_name", None)}, file={getattr(obj, "file", None)}')
        if obj.file:
            try:
                s3_client = boto3.client(
                    's3',
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                    region_name=settings.AWS_S3_REGION_NAME
                )
                presigned_url = s3_client.generate_presigned_url(
                    'get_object',
                    Params={
                        'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
                        'Key': obj.file
                    },
                    ExpiresIn=60*10  # 10분간 유효
                )
                display_name = obj.original_name if obj.original_name else os.path.basename(obj.file)
                return format_html('<a href="{}" target="_blank">{}</a>', presigned_url, display_name)
            except Exception as e:
                display_name = obj.original_name if obj.original_name else os.path.basename(obj.file)
                return format_html('<a href="{}" target="_blank">{}</a> (url 오류)', obj.file, display_name)
        return "-"
    file_link.short_description = '다운로드 링크'

    # def file_size(self, obj):
    #     ... (주석처리)
    # file_size.short_description = '파일 크기'

    # def preview(self, obj):
    #     ... (주석처리)
    # preview.short_description = '미리보기'

# @admin.register(Request)  # 사이드바에서 숨김
class RequestAdmin(ModelAdmin):
    list_display = (
        'id', 'name', 'email', 'phone', 'status', 
        'recording_date', 'recording_location', 'speaker_count',
        'estimated_price', 'draft_format', 'final_option', 'created_at', 'file_count'
    )
    list_filter = ('status', 'created_at', 'draft_format', 'final_option', 'speaker_count')
    search_fields = ('name', 'email', 'phone', 'recording_location')
    readonly_fields = ('created_at', 'updated_at', 'agreement')
    inlines = [FileInline]
    list_per_page = 50
    list_editable = ('status', 'draft_format', 'final_option')
    actions = ['mark_completed', 'mark_in_progress', 'export_to_csv']

    fieldsets = (
        ('기본 정보', {
            'fields': ('name', 'email', 'phone', 'address')
        }),
        ('녹음 정보', {
            'fields': ('recording_date', 'recording_location', 'speaker_count', 'speaker_info', 'has_detail', 'detail_info', 'estimated_price')
        }),
        ('상세 정보', {
            'fields': ('status', 'agreement', 'created_at', 'updated_at')
        })
    )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj is None:  # 새로운 객체 생성 시
            form.base_fields['agreement'].initial = True
        return form

    def save_model(self, request, obj, form, change):
        obj.agreement = True  # 저장 시 항상 True로 설정
        super().save_model(request, obj, form, change)

    def delete_model(self, request, obj):
        s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
        )
        for file in obj.files.all():
            try:
                print(f'[ADMIN delete_model] Deleting file from S3: {file.file}')
                s3_client.delete_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=file.file)
            except Exception as e:
                print(f'[ADMIN delete_model] Failed to delete file from S3: {str(e)}')
                pass
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
        )
        for req in queryset:
            for file in req.files.all():
                try:
                    print(f'[ADMIN delete_queryset] Deleting file from S3: {file.file}')
                    s3_client.delete_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=file.file)
                except Exception as e:
                    print(f'[ADMIN delete_queryset] Failed to delete file from S3: {str(e)}')
                    pass
        super().delete_queryset(request, queryset)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(is_temporary=False)
    
    def file_count(self, obj):
        return obj.files.count()
    file_count.short_description = '첨부파일 수'
    
    def mark_completed(self, request, queryset):
        queryset.update(status='completed')
        self.message_user(request, f'{queryset.count()}개 요청을 완료로 변경했습니다.')
    mark_completed.short_description = '선택된 요청을 완료로 변경'
    
    def mark_in_progress(self, request, queryset):
        queryset.update(status='in_progress')
        self.message_user(request, f'{queryset.count()}개 요청을 진행중으로 변경했습니다.')
    mark_in_progress.short_description = '선택된 요청을 진행중으로 변경'
    
    def export_to_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="requests.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'ID', '이름', '이메일', '전화번호', '상태', '녹음일시', 
            '녹음장소', '화자수', '예상견적', '원고형식', '최종옵션', '생성일'
        ])
        
        for obj in queryset:
            writer.writerow([
                obj.id, obj.name, obj.email, obj.phone, obj.get_status_display(),
                obj.recording_date, obj.recording_location, obj.speaker_count,
                obj.estimated_price, obj.get_draft_format_display(), obj.get_final_option_display(),
                obj.created_at.strftime('%Y-%m-%d %H:%M')
            ])
        
        return response
    export_to_csv.short_description = 'CSV로 내보내기'

# @admin.register(Template)  # 사이드바에서 숨김
class TemplateAdmin(ModelAdmin):
    list_display = ('name', 'type', 'last_modified')
    list_filter = ('type',)
    search_fields = ('name', 'content')

@admin.register(SendLog)
class SendLogAdmin(ModelAdmin):
    list_display = ('id', 'request', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('request__name',)
    readonly_fields = ('created_at', 'updated_at')

    def has_add_permission(self, request):
        return False

# @admin.register(ExcelDatabase)  # 사이드바에서 숨김 (database/admin.py의 ExcelView 사용)
class ExcelDatabaseAdmin(ModelAdmin):
    list_display = (
        'id', 'name', 'email', 'phone', 'status_display', 
        'recording_date', 'recording_location', 'speaker_count',
        'estimated_price', 'draft_format', 'final_option', 'created_at'
    )
    list_filter = ('status', 'created_at', 'draft_format', 'final_option', 'speaker_count')
    search_fields = ('name', 'email', 'phone', 'recording_location')
    list_per_page = 50
    
    # 테이블 스타일링을 위한 템플릿 오버라이드
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



