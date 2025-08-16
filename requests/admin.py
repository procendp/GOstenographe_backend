from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.conf import settings
from .models import Request, Template, SendLog, File
from django.utils import timezone
from datetime import datetime, time
import boto3
import os

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

@admin.register(Request)
class RequestAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('name', 'email', 'phone')
    readonly_fields = ('created_at', 'updated_at', 'agreement')
    inlines = [FileInline]

    fieldsets = (
        ('기본 정보', {
            'fields': ('name', 'email', 'phone', 'address')
        }),
        ('녹음 정보', {
            'fields': ('recording_date', 'recording_location', 'speaker_count', 'speaker_info', 'has_detail', 'detail_info')
        }),
        ('기타 정보', {
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

@admin.register(Template)
class TemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'last_modified')
    list_filter = ('type',)
    search_fields = ('name', 'content')

@admin.register(SendLog)
class SendLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'request', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('request__name',)
    readonly_fields = ('created_at', 'updated_at')
