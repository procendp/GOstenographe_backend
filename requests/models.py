from django.db import models
from django.core.validators import FileExtensionValidator, MaxValueValidator, MinValueValidator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import boto3
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class Request(models.Model):
    STATUS_CHOICES = (
        ('pending', _('대기중')),
        ('in_progress', _('진행중')),
        ('completed', _('완료')),
        ('cancelled', _('취소')),
    )
    
    DRAFT_FORMAT_CHOICES = (
        ('hwp', _('hwp')),
        ('txt', _('txt')),
        ('docx', _('docx')),
    )
    
    FINAL_OPTION_CHOICES = (
        ('file', _('파일')),
        ('file_usb', _('파일+우편')),
        ('file_usb_post', _('파일+우편+USB')),
    )

    # 기본 정보
    name = models.CharField(_('이름'), max_length=100)
    email = models.EmailField(_('이메일'))
    phone = models.CharField(_('전화번호'), max_length=20)
    address = models.CharField(_('주소'), max_length=255, blank=True)
    
    # 녹음 정보
    recording_date = models.DateTimeField(_('녹음 일시'), null=True, blank=True)
    recording_location = models.CharField(_('녹음 장소'), max_length=200, blank=True)
    speaker_count = models.IntegerField(
        _('화자 수'),
        default=1,
        validators=[
            MinValueValidator(1, message='화자 수는 최소 1명 이상이어야 합니다.'),
            MaxValueValidator(5, message='화자 수는 최대 5명까지 가능합니다.')
        ]
    )
    speaker_info = models.JSONField(_('화자 정보'), default=list, blank=True)
    has_detail = models.BooleanField(_('세부 내용'), default=False)
    detail_info = models.TextField(_('세부 내용 정보'), blank=True)
    
    # 기타 정보
    status = models.CharField(
        _('상태'),
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    draft_format = models.CharField(_('원고 형식'), max_length=20, choices=DRAFT_FORMAT_CHOICES, default='hwp')
    final_option = models.CharField(_('최종 옵션'), max_length=20, choices=FINAL_OPTION_CHOICES, default='file')
    agreement = models.BooleanField(_('동의'), default=True)
    created_at = models.DateTimeField(_('생성일'), auto_now_add=True)
    updated_at = models.DateTimeField(_('수정일'), auto_now=True)
    is_temporary = models.BooleanField('임시 신청서 여부', default=True)

    class Meta:
        verbose_name = _('요청서')
        verbose_name_plural = _('요청서')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.get_status_display()}"

    def get_status_display(self):
        status_map = {
            'pending': '대기중',
            'processing': '처리중',
            'completed': '완료',
            'cancelled': '취소'
        }
        return status_map.get(self.status, self.status)

class Template(models.Model):
    name = models.CharField(_('템플릿명'), max_length=100)
    type = models.CharField(
        _('타입'),
        max_length=10,
        choices=[('sms', 'SMS'), ('email', 'Email')]
    )
    content = models.TextField(_('메시지 내용'))
    last_modified = models.DateTimeField(_('마지막 수정일'), auto_now=True)
    
    class Meta:
        verbose_name = _('템플릿')
        verbose_name_plural = _('템플릿 목록')

class SendLog(models.Model):
    request = models.ForeignKey(
        'Request',
        on_delete=models.CASCADE,
        verbose_name=_('신청서'),
        related_name='sendlog_set',
        null=True,
        blank=True
    )
    error_message = models.TextField(
        verbose_name=_('에러 메시지'),
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(
        verbose_name=_('생성일'),
        default=timezone.now
    )
    updated_at = models.DateTimeField(
        verbose_name=_('수정일'),
        auto_now=True
    )

    class Meta:
        verbose_name = _('발송 로그')
        verbose_name_plural = _('발송 로그')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.request} - {self.created_at}"

class File(models.Model):
    request = models.ForeignKey(Request, on_delete=models.CASCADE, related_name='files', verbose_name=_('요청서'))
    file = models.CharField(max_length=255)  # S3 파일 키를 저장
    original_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=50)
    file_size = models.BigIntegerField(default=0)  # 기본값 0으로 설정
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('첨부파일')
        verbose_name_plural = _('첨부 파일')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.original_name} ({self.created_at})"

    def delete(self, *args, **kwargs):
        # S3에서 파일 삭제
        s3_client = boto3.client('s3')
        try:
            s3_client.delete_object(
                Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                Key=self.file
            )
        except Exception as e:
            logger.error(f"Failed to delete file from S3: {str(e)}")
        super().delete(*args, **kwargs)
