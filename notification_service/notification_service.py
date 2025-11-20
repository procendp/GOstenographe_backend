"""
통합 알림 서비스 - SMS, Email 발송 관리
"""
import logging
from .sms_sender import NaverCloudSMS
from .email_sender import ResendEmail
from .template_engine import TemplateEngine

# Django 앱 모델을 명시적으로 로드 (HTTP requests 라이브러리 충돌 방지)
from django.apps import apps
SendLog = apps.get_model('requests', 'SendLog')
StatusChangeLog = apps.get_model('requests', 'StatusChangeLog')

logger = logging.getLogger(__name__)


class NotificationService:
    """통합 알림 서비스"""
    
    def __init__(self):
        self.sms_sender = NaverCloudSMS()
        self.email_sender = ResendEmail()
        self.template_engine = TemplateEngine()
    
    def send_status_notification(self, request_obj, new_status, old_status=None, send_sms=True, send_email=True):
        """
        상태 변경 알림 발송
        
        Args:
            request_obj: Request 인스턴스
            new_status: 새로운 상태
            old_status: 이전 상태 (선택)
            send_sms: SMS 발송 여부
            send_email: 이메일 발송 여부
            
        Returns:
            dict: 발송 결과
        """
        results = {
            'sms': None,
            'email': None,
            'success': False,
            'errors': []
        }
        
        try:
            # SMS 발송
            if send_sms and request_obj.phone:
                sms_result = self._send_sms_notification(request_obj, new_status)
                results['sms'] = sms_result
                
                # 발송 로그 기록
                self._create_send_log(request_obj, 'sms', new_status, sms_result)
            
            # Email 발송
            if send_email and request_obj.email:
                email_result = self._send_email_notification(request_obj, new_status)
                results['email'] = email_result
                
                # 발송 로그 기록
                self._create_send_log(request_obj, 'email', new_status, email_result)
            
            # 전체 성공 여부 판단
            sms_success = not send_sms or (results['sms'] and results['sms']['success'])
            email_success = not send_email or (results['email'] and results['email']['success'])
            results['success'] = sms_success and email_success
            
            # 상태 변경 로그에 알림 발송 여부 기록
            self._update_status_change_log(request_obj, new_status, results['success'])
            
            return results
            
        except Exception as e:
            logger.error(f"알림 발송 중 오류: {str(e)}")
            results['errors'].append(str(e))
            return results
    
    def _send_sms_notification(self, request_obj, status):
        """SMS 알림 발송"""
        try:
            # 템플릿 준비
            notification_data = self.template_engine.prepare_notification(
                request_obj, status, 'sms'
            )
            
            # SMS 발송
            result = self.sms_sender.send_sms(
                to_number=request_obj.phone,
                content=notification_data['content']
            )
            
            logger.info(f"SMS 발송 완료: {request_obj.name} ({request_obj.phone})")
            return result
            
        except Exception as e:
            logger.error(f"SMS 발송 실패: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _send_email_notification(self, request_obj, status):
        """이메일 알림 발송"""
        try:
            # 템플릿 준비
            notification_data = self.template_engine.prepare_notification(
                request_obj, status, 'email'
            )
            
            # 이메일 발송
            result = self.email_sender.send_email(
                to_email=request_obj.email,
                subject=notification_data['subject'],
                content=notification_data['content']
            )
            
            logger.info(f"이메일 발송 완료: {request_obj.name} ({request_obj.email})")
            return result
            
        except Exception as e:
            logger.error(f"이메일 발송 실패: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _create_send_log(self, request_obj, notification_type, status, result):
        """발송 로그 생성"""
        try:
            error_message = None
            if not result['success']:
                error_message = result.get('error', '발송 실패')
            
            SendLog.objects.create(
                request=request_obj,
                error_message=error_message
            )
            
        except Exception as e:
            logger.error(f"발송 로그 생성 실패: {str(e)}")
    
    def _update_status_change_log(self, request_obj, status, notification_sent):
        """상태 변경 로그에 알림 발송 여부 업데이트"""
        try:
            # 가장 최근 상태 변경 로그 찾기
            latest_log = StatusChangeLog.objects.filter(
                request=request_obj,
                to_status=status
            ).order_by('-changed_at').first()
            
            if latest_log:
                latest_log.notification_sent = notification_sent
                latest_log.save()
                
        except Exception as e:
            logger.error(f"상태 변경 로그 업데이트 실패: {str(e)}")
    
    def send_test_notification(self, phone=None, email=None):
        """
        테스트 알림 발송
        
        Args:
            phone: 테스트 SMS 수신 번호
            email: 테스트 이메일 주소
            
        Returns:
            dict: 테스트 결과
        """
        results = {
            'sms': None,
            'email': None
        }
        
        # SMS 테스트
        if phone:
            test_content = "속기사무소 정 SMS 테스트 메시지입니다."
            results['sms'] = self.sms_sender.send_sms(phone, test_content)
        
        # 이메일 테스트
        if email:
            test_subject = "[속기사무소 정] 이메일 테스트"
            test_content = "속기사무소 정 이메일 테스트 메시지입니다."
            results['email'] = self.email_sender.send_email(email, test_subject, test_content)
        
        return results
    
    def get_notification_settings(self, status):
        """
        상태별 알림 발송 설정
        
        Args:
            status: 상태 코드
            
        Returns:
            dict: {
                'send_sms': bool,
                'send_email': bool
            }
        """
        # 상태별 발송 규칙 (나중에 데이터베이스나 설정 파일로 관리 가능)
        notification_rules = {
            'received': {'sms': False, 'email': True},  # SMS 설정 완료 시 True로 변경
            'payment_completed': {'sms': False, 'email': True},  # SMS 설정 완료 시 True로 변경
            'in_progress': {'sms': False, 'email': True},
            'work_completed': {'sms': False, 'email': True},  # SMS 설정 완료 시 True로 변경
            'sent': {'sms': False, 'email': True},  # SMS 설정 완료 시 True로 변경
            'cancelled': {'sms': False, 'email': True},  # SMS 설정 완료 시 True로 변경
            'refunded': {'sms': False, 'email': True},  # SMS 설정 완료 시 True로 변경
            'impossible': {'sms': False, 'email': True}  # SMS 설정 완료 시 True로 변경
        }
        
        return notification_rules.get(status, {'sms': False, 'email': False})


# 전역 인스턴스
notification_service = NotificationService()