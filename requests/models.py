from django.db import models
from django.core.validators import FileExtensionValidator, MaxValueValidator, MinValueValidator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import boto3
from django.conf import settings
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class Request(models.Model):
    # 기존 상태 (Request 레벨 - 개별 파일 작업 상태)
    STATUS_CHOICES = (
        ('received', _('접수됨')),
        ('in_progress', _('작업중')),
        ('work_completed', _('작업완료')),
        ('sent', _('발송완료')),
        ('impossible', _('작업불가')),
        ('cancelled', _('취소됨')),
    )
    
    # Order 레벨 상태 (주문 전체 상태)
    ORDER_STATUS_CHOICES = (
        ('received', _('접수됨')),
        ('payment_completed', _('결제완료')),
        ('sent', _('발송완료')),
        ('impossible', _('작업불가')),
        ('cancelled', _('취소됨')),
        ('refunded', _('환불완료')),
    )

    DRAFT_FORMAT_CHOICES = (
        ('hwp', _('hwp')),
        ('txt', _('txt')),
        ('docx', _('docx')),
    )
    
    FINAL_OPTION_CHOICES = (
        ('file', _('파일')),
        ('file_usb', _('파일 + 등기 우편 (+5,000원)')),
        ('file_usb_cd', _('파일 + 등기 우편 + CD (+6,000원)')),
        ('file_usb_post', _('파일 + 등기 우편 + USB (+10,000원)')),
    )

    # 기본 정보
    name = models.CharField(_('이름'), max_length=100)
    email = models.EmailField(_('이메일'))
    phone = models.CharField(_('전화번호'), max_length=20)
    address = models.CharField(_('주소'), max_length=255, blank=True)
    
    # 녹음 정보
    recording_date = models.DateTimeField(_('녹음 일시'), null=True, blank=True)
    recording_location = models.CharField(_('녹음 종류'), max_length=200, blank=True)
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
        _('Request 상태'),
        max_length=20,
        choices=STATUS_CHOICES,
        default='received',
        help_text='개별 파일 작업 상태'
    )
    order_status = models.CharField(
        _('Order 상태'),
        max_length=20,
        choices=ORDER_STATUS_CHOICES,
        default='received',
        help_text='주문 전체 상태'
    )
    draft_format = models.CharField(_('원고 형식'), max_length=20, choices=DRAFT_FORMAT_CHOICES, default='hwp')
    final_option = models.CharField(_('최종 옵션'), max_length=20, choices=FINAL_OPTION_CHOICES, default='file')
    agreement = models.BooleanField(_('동의'), default=True)
    created_at = models.DateTimeField(_('생성일'), auto_now_add=True)
    updated_at = models.DateTimeField(_('수정일'), auto_now=True)
    is_temporary = models.BooleanField('임시 신청서 여부', default=True)
    
    # 추가 필드들 (엑셀 데이터베이스용)
    order_id = models.CharField(_('Order ID'), max_length=10, null=True, blank=True)  # YYMMDD+00~99 형식
    request_id = models.CharField(_('Request ID'), max_length=50, unique=True, blank=True)  # OrderID+00~99 형식
    recording_type = models.CharField(_('녹취 타입'), max_length=20, default='전체')
    partial_range = models.CharField(_('부분 녹취 구간'), max_length=100, blank=True)
    total_duration = models.CharField(_('총 길이'), max_length=50, blank=True)
    speaker_names = models.TextField(_('화자 이름'), blank=True)
    additional_info = models.TextField(_('상세 정보'), blank=True)
    estimated_price = models.DecimalField(_('예상 견적'), max_digits=10, decimal_places=0, null=True, blank=True)
    payment_status = models.BooleanField(_('결제 여부'), default=False)
    payment_amount = models.DecimalField(_('결제 금액'), max_digits=10, decimal_places=0, null=True, blank=True)
    price_change_reason = models.TextField(_('결제금액 변동 사유'), blank=True)
    refund_amount = models.DecimalField(_('환불 금액'), max_digits=10, decimal_places=0, null=True, blank=True)
    cancel_reason = models.TextField(_('취소 사유'), blank=True)
    impossible_reason = models.TextField(_('작업불가 사유'), blank=True)
    transcript_file = models.ForeignKey('File', on_delete=models.SET_NULL, null=True, blank=True, related_name='transcript_requests', verbose_name=_('속기록 파일'))
    notes = models.TextField(_('상세 정보'), blank=True)

    class Meta:
        verbose_name = _('요청서')
        verbose_name_plural = _('요청서')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.get_status_display()}"

    def get_status_display(self):
        """Request 상태 표시"""
        status_map = {
            'received': '접수됨',
            'in_progress': '작업중',
            'work_completed': '작업완료',
            'sent': '발송완료',
            'impossible': '작업불가',
            'cancelled': '취소됨'
        }
        return status_map.get(self.status, self.status)
    
    def get_order_status_display(self):
        """Order 상태 표시"""
        order_status_map = {
            'received': '접수됨',
            'payment_completed': '결제완료',
            'sent': '발송완료',
            'impossible': '작업불가',
            'cancelled': '취소됨',
            'refunded': '환불완료'
        }
        return order_status_map.get(self.order_status, self.order_status)
    
    def can_change_to(self, new_status):
        """현재 상태에서 변경 가능한 상태인지 확인"""
        allowed_transitions = {
            'received': ['payment_completed', 'impossible', 'cancelled'],
            'payment_completed': ['in_progress', 'cancelled'],
            'in_progress': ['work_completed', 'impossible'],
            'work_completed': ['sent'],
            'sent': [],  # 발송완료는 최종 상태
            'impossible': ['cancelled', 'refunded'],
            'cancelled': ['refunded'],
            'refunded': []  # 환불완료는 최종 상태
        }
        return new_status in allowed_transitions.get(self.status, [])
    
    @classmethod
    def get_next_order_counter(cls, is_db_order=False):
        """전역 주문 카운터 반환

        Args:
            is_db_order (bool): DB 주문 여부

        Returns:
            int: 다음 카운터 값
                - 일반 주문: 00~99 (2자리)
                - DB 주문: 0000~9999 (4자리)
        """
        if is_db_order:
            # DB 주문: DB + YYMMDD + 0000~9999 형식
            last_order = cls.objects.filter(
                order_id__isnull=False,
                order_id__startswith='DB',
                order_id__regex=r'^DB\d{6}\d{4}$'  # DBYYMMDDNNNN 형식 확인
            ).order_by('-created_at').first()

            if last_order and last_order.order_id:
                # Order ID의 마지막 4자리 추출
                counter = int(last_order.order_id[-4:])
                # 9999 다음은 0000으로 리셋
                next_counter = (counter + 1) % 10000
                return next_counter
            return 0  # 첫 번째 주문은 0000
        else:
            # 일반 주문: YYMMDD + 00~99 형식
            last_order = cls.objects.filter(
                order_id__isnull=False,
                order_id__regex=r'^\d{6}\d{2}$'  # YYMMDDNN 형식 확인
            ).order_by('-created_at').first()

            if last_order and last_order.order_id:
                # Order ID의 마지막 2자리 추출
                counter = int(last_order.order_id[-2:])
                # 99 다음은 00으로 리셋
                next_counter = (counter + 1) % 100
                return next_counter
            return 0  # 첫 번째 주문은 00

    @classmethod
    def generate_order_id(cls, is_db_order=False):
        """Order ID 생성

        Args:
            is_db_order (bool): DB 주문 여부

        Returns:
            str: 생성된 Order ID
                - 일반 주문: YYMMDD + 00~99 (예: 25100700)
                - DB 주문: DB + YYMMDD + 0000~9999 (예: DB2510070000)
        """
        today = datetime.now()
        date_str = today.strftime('%y%m%d')
        counter = cls.get_next_order_counter(is_db_order=is_db_order)

        if is_db_order:
            return f"DB{date_str}{counter:04d}"
        else:
            return f"{date_str}{counter:02d}"
    
    @classmethod 
    def generate_request_id(cls, order_id):
        """Request ID 생성 (OrderID + 파일순번 00~99)"""
        if not order_id:
            raise ValueError("Order ID is required for Request ID generation")
        
        # 같은 Order ID를 가진 Request들의 개수 확인
        existing_count = cls.objects.filter(order_id=order_id).count()
        
        # Request ID = Order ID + 파일 순번 (00부터 시작)
        return f"{order_id}{existing_count:02d}"
    
    def save(self, *args, **kwargs):
        """저장 시 Order ID와 Request ID 자동 생성"""
        # skip_auto_email 플래그 추출 (File 생성 전 이메일 발송 방지)
        skip_auto_email = kwargs.pop('skip_auto_email', False)

        is_new_record = not self.pk

        # 새로운 레코드인 경우에만 ID 생성
        if is_new_record:  # 새로운 레코드
            # Order ID가 없으면 생성
            if not self.order_id:
                self.order_id = self.generate_order_id()

            # Request ID가 없으면 생성
            if not self.request_id:
                self.request_id = self.generate_request_id(self.order_id)

        super().save(*args, **kwargs)

        # 새로운 레코드이고 임시가 아니며, skip_auto_email=False인 경우만 이메일 발송
        if is_new_record and not self.is_temporary and not skip_auto_email:
            self.send_application_completion_guide()
    
    def send_application_completion_guide(self):
        """서비스 신청 완료 안내 자동 발송"""
        try:
            from notification_service.bulk_email_service import BulkEmailService
            
            print(f'[AUTO SEND EMAIL] 서비스 신청 완료 안내 발송 - Request ID: {self.request_id}, Email: {self.email}')
            logger.info(f'서비스 신청 완료 안내 발송 - Request ID: {self.request_id}, Email: {self.email}')
            
            # 같은 이메일 주소의 모든 요청 가져오기 (같은 주문 건)
            same_email_requests = Request.objects.filter(
                email=self.email,
                order_id=self.order_id,
                is_temporary=False
            ).order_by('created_at')
            
            # 첫 번째 요청에서만 이메일 발송 (중복 발송 방지)
            first_request = same_email_requests.first()
            if first_request.id != self.id:
                logger.info(f'중복 발송 방지 - 첫 번째 요청이 아님: {self.request_id}')
                return
            
            # 대량 이메일 서비스 사용 (첨부파일 없음)
            bulk_service = BulkEmailService()
            result = bulk_service.send_service_completion_guide(
                requests=list(same_email_requests),
                email_subject='서비스 신청 완료 안내'
            )
            
            if result['success_count'] > 0:
                logger.info(f'서비스 신청 완료 안내 발송 성공 - Order ID: {self.order_id}, Email: {self.email}')
            else:
                logger.error(f'서비스 신청 완료 안내 발송 실패 - Order ID: {self.order_id}, Errors: {result["failed_emails"]}')
                
        except Exception as e:
            logger.error(f'서비스 신청 완료 안내 발송 실패 - Request ID: {self.request_id}, Error: {str(e)}')

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
    EMAIL_TYPE_CHOICES = (
        ('service_completion', _('서비스 신청 완료 안내')),
        ('quotation_guide', _('견적 및 입금 안내')),
        ('payment_completion_guide', _('결제 완료 안내')),
        ('draft_guide', _('속기록 초안/수정안 발송')),
        ('final_draft_guide', _('속기록 최종안 발송')),
    )

    request = models.ForeignKey(
        'Request',
        on_delete=models.CASCADE,
        verbose_name=_('신청서'),
        related_name='sendlog_set',
        null=True,
        blank=True
    )
    email_type = models.CharField(
        verbose_name=_('이메일 종류'),
        max_length=50,
        choices=EMAIL_TYPE_CHOICES,
        null=True,
        blank=True
    )
    order_id = models.CharField(
        verbose_name=_('Order ID'),
        max_length=10,
        null=True,
        blank=True,
        help_text='발송 시점의 Order ID'
    )
    sent_request_id = models.CharField(
        verbose_name=_('Request ID'),
        max_length=50,
        null=True,
        blank=True,
        help_text='발송 시점의 Request ID (초안/최종안용)'
    )
    payment_amount = models.DecimalField(
        verbose_name=_('안내 금액'),
        max_digits=10,
        decimal_places=0,
        null=True,
        blank=True,
        help_text='발송 시점의 결제 금액'
    )
    recipient_email = models.EmailField(
        verbose_name=_('수신자 이메일'),
        null=True,
        blank=True
    )
    success = models.BooleanField(
        verbose_name=_('발송 성공 여부'),
        default=True
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
        indexes = [
            models.Index(fields=['order_id', 'email_type', '-created_at']),
            models.Index(fields=['sent_request_id', 'email_type', '-created_at']),
            models.Index(fields=['recipient_email', 'email_type', '-created_at']),
        ]

    def __str__(self):
        return f"{self.get_email_type_display()} - {self.order_id or self.request} - {self.created_at}"

class File(models.Model):
    request = models.ForeignKey(
        Request,
        on_delete=models.CASCADE,
        related_name='files',
        verbose_name=_('요청서'),
        null=True,      # 속기록 파일은 Request와 직접 연결되지 않도록 허용
        blank=True
    )
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

class StatusChangeLog(models.Model):
    """상태 변경 이력 추적"""
    request = models.ForeignKey(Request, on_delete=models.CASCADE, related_name='status_logs')
    from_status = models.CharField(max_length=20, blank=True, null=True)
    to_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey('core.User', on_delete=models.SET_NULL, null=True)
    changed_at = models.DateTimeField(auto_now_add=True)
    reason = models.TextField(blank=True, help_text="상태 변경 사유")
    notification_sent = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = _('상태 변경 이력')
        verbose_name_plural = _('상태 변경 이력')
        ordering = ['-changed_at']
    
    def __str__(self):
        return f"{self.request} - {self.from_status} -> {self.to_status}"

class ExcelDatabase(Request):
    """엑셀 뷰를 위한 프록시 모델"""
    
    class Meta:
        proxy = True
        verbose_name = _('엑셀 데이터베이스')
        verbose_name_plural = _('엑셀 뷰')
        
    def __str__(self):
        return f"{self.name} - {self.get_status_display()}"

