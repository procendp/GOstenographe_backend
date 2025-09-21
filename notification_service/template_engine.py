"""
템플릿 엔진 - 변수 치환 및 템플릿 관리
"""
import re
import logging
from datetime import datetime
from requests.models import Template, Request

logger = logging.getLogger(__name__)


class TemplateEngine:
    """템플릿 변수 치환 엔진"""
    
    @staticmethod
    def get_variables_from_request(request_obj):
        """
        Request 객체에서 템플릿 변수 추출
        
        Args:
            request_obj: Request 모델 인스턴스
            
        Returns:
            dict: 템플릿 변수 딕셔너리
        """
        return {
            # 기본 정보
            'name': request_obj.name,
            'email': request_obj.email,
            'phone': request_obj.phone,
            'address': request_obj.address or '',
            
            # ID 정보
            'order_id': str(request_obj.order_id) if request_obj.order_id else '',
            'request_id': request_obj.request_id or str(request_obj.id),
            
            # 상태 정보
            'status': request_obj.get_status_display(),
            'status_code': request_obj.status,
            
            # 녹음 정보
            'recording_date': request_obj.recording_date.strftime('%Y년 %m월 %d일') if request_obj.recording_date else '',
            'recording_location': request_obj.recording_location or '',
            'speaker_count': str(request_obj.speaker_count),
            'speaker_names': request_obj.speaker_names or '',
            'total_duration': request_obj.total_duration or '',
            
            # 가격 정보
            'estimated_price': f"{request_obj.estimated_price:,.0f}원" if request_obj.estimated_price else '',
            'payment_amount': f"{request_obj.payment_amount:,.0f}원" if request_obj.payment_amount else '',
            'payment_status': '결제완료' if request_obj.payment_status else '미결제',
            
            # 옵션 정보
            'draft_format': request_obj.get_draft_format_display(),
            'final_option': request_obj.get_final_option_display(),
            
            # 날짜/시간
            'today': datetime.now().strftime('%Y년 %m월 %d일'),
            'now': datetime.now().strftime('%H시 %M분'),
            
            # 회사 정보
            'company': '속기사무소 정',
            'company_phone': '070-1234-5678',  # 실제 번호로 변경 필요
            'company_email': 'procendp@gmail.com',
        }
    
    @staticmethod
    def replace_variables(template_content, variables):
        """
        템플릿 내용의 변수를 실제 값으로 치환
        
        Args:
            template_content: 템플릿 내용 (변수는 {variable_name} 형식)
            variables: 변수 딕셔너리
            
        Returns:
            str: 치환된 내용
        """
        result = template_content
        
        # {variable_name} 패턴 찾기
        pattern = r'\{([^}]+)\}'
        matches = re.findall(pattern, template_content)
        
        for match in matches:
            if match in variables:
                # 변수 값이 None이면 빈 문자열로 치환
                value = variables[match] if variables[match] is not None else ''
                result = result.replace(f'{{{match}}}', str(value))
            else:
                logger.warning(f"템플릿 변수 '{match}'를 찾을 수 없습니다.")
        
        return result
    
    @staticmethod
    def get_template_by_status(status, notification_type):
        """
        상태와 타입에 맞는 템플릿 가져오기
        
        Args:
            status: 상태 코드 (received, payment_completed, etc.)
            notification_type: 'sms' 또는 'email'
            
        Returns:
            Template: 템플릿 객체 또는 None
        """
        try:
            # 템플릿 이름 규칙: status_type (예: payment_completed_sms)
            template_name = f"{status}_{notification_type}"
            template = Template.objects.filter(
                name__icontains=status,
                type=notification_type
            ).first()
            
            if not template:
                # 기본 템플릿 찾기
                template = Template.objects.filter(
                    name__icontains='default',
                    type=notification_type
                ).first()
                
                if not template:
                    logger.warning(f"템플릿을 찾을 수 없습니다: {template_name}")
            
            return template
            
        except Exception as e:
            logger.error(f"템플릿 조회 중 오류: {str(e)}")
            return None
    
    @staticmethod
    def prepare_notification(request_obj, status, notification_type):
        """
        알림 발송을 위한 컨텐츠 준비
        
        Args:
            request_obj: Request 인스턴스
            status: 상태 코드
            notification_type: 'sms' 또는 'email'
            
        Returns:
            dict: {
                'subject': 제목 (이메일용),
                'content': 내용,
                'template_used': 사용된 템플릿
            }
        """
        # 템플릿 가져오기
        template = TemplateEngine.get_template_by_status(status, notification_type)
        
        if not template:
            # 템플릿이 없으면 기본 메시지
            default_messages = {
                'received': {
                    'sms': '안녕하세요 {name}님, 속기사무소 정입니다. 주문번호 {request_id}번 접수가 완료되었습니다.',
                    'email': '안녕하세요 {name}님,\n\n속기사무소 정입니다.\n주문번호 {request_id}번 접수가 완료되었습니다.\n\n감사합니다.'
                },
                'payment_completed': {
                    'sms': '{name}님, 결제가 완료되었습니다. 곧 작업을 시작하겠습니다.',
                    'email': '{name}님, 결제가 완료되었습니다.\n\n작업이 시작되면 다시 안내드리겠습니다.'
                },
                'in_progress': {
                    'sms': '{name}님, 속기 작업을 시작했습니다.',
                    'email': '{name}님, 주문번호 {request_id}번의 속기 작업을 시작했습니다.'
                },
                'work_completed': {
                    'sms': '{name}님, 속기 작업이 완료되었습니다. 곧 발송 예정입니다.',
                    'email': '{name}님, 속기 작업이 완료되었습니다.\n\n최종 검토 후 발송하겠습니다.'
                },
                'sent': {
                    'sms': '{name}님, 속기록이 발송되었습니다. 이메일을 확인해주세요.',
                    'email': '{name}님, 속기록을 발송했습니다.\n\n첨부파일을 확인해주세요.'
                }
            }
            
            content = default_messages.get(status, {}).get(
                notification_type, 
                f'{name}님, 주문 상태가 변경되었습니다.'
            )
        else:
            content = template.content
        
        # 변수 치환
        variables = TemplateEngine.get_variables_from_request(request_obj)
        final_content = TemplateEngine.replace_variables(content, variables)
        
        # 이메일 제목 생성
        subject = None
        if notification_type == 'email':
            status_subjects = {
                'received': '[속기사무소 정] 접수 완료 안내',
                'payment_completed': '[속기사무소 정] 결제 완료 안내',
                'in_progress': '[속기사무소 정] 작업 시작 안내',
                'work_completed': '[속기사무소 정] 작업 완료 안내',
                'sent': '[속기사무소 정] 속기록 발송 완료',
                'cancelled': '[속기사무소 정] 주문 취소 안내',
                'refunded': '[속기사무소 정] 환불 완료 안내'
            }
            subject = status_subjects.get(status, '[속기사무소 정] 알림')
            
            # 제목에도 변수 치환 적용
            subject = TemplateEngine.replace_variables(subject, variables)
        
        return {
            'subject': subject,
            'content': final_content,
            'template_used': template.name if template else 'default'
        }
    
    @staticmethod
    def validate_template(content):
        """
        템플릿 유효성 검사
        
        Args:
            content: 템플릿 내용
            
        Returns:
            dict: {
                'valid': bool,
                'variables': 발견된 변수 리스트,
                'errors': 오류 메시지
            }
        """
        pattern = r'\{([^}]+)\}'
        variables = re.findall(pattern, content)
        
        # 사용 가능한 변수 목록
        available_vars = [
            'name', 'email', 'phone', 'address',
            'order_id', 'request_id', 'status',
            'recording_date', 'speaker_count', 'total_duration',
            'estimated_price', 'payment_amount', 'payment_status',
            'draft_format', 'final_option',
            'today', 'now', 'company', 'company_phone', 'company_email'
        ]
        
        errors = []
        for var in variables:
            if var not in available_vars:
                errors.append(f"알 수 없는 변수: {{{var}}}")
        
        return {
            'valid': len(errors) == 0,
            'variables': variables,
            'errors': errors
        }