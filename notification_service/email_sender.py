"""
SendGrid Email 발송 서비스
"""
import os
import logging
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content, Attachment
from django.conf import settings
import base64
import mimetypes

logger = logging.getLogger(__name__)


class SendGridEmail:
    """SendGrid 이메일 발송 클래스"""
    
    def __init__(self):
        self.api_key = getattr(settings, 'SENDGRID_API_KEY', os.getenv('SENDGRID_API_KEY'))
        self.from_email = getattr(settings, 'SENDGRID_FROM_EMAIL', os.getenv('SENDGRID_FROM_EMAIL', 'procendp@gmail.com'))
        self.from_name = getattr(settings, 'SENDGRID_FROM_NAME', os.getenv('SENDGRID_FROM_NAME', '속기사무소 정'))
        
        if not self.api_key:
            logger.warning("SendGrid API 키가 설정되지 않았습니다. .env 파일을 확인하세요.")
    
    def send_email(self, to_email, subject, content, content_type='text/plain', attachments=None):
        """
        이메일 발송
        
        Args:
            to_email: 수신 이메일
            subject: 제목
            content: 내용
            content_type: 'text/plain' 또는 'text/html'
            attachments: 첨부파일 리스트 [{'file_content': bytes, 'filename': str, 'file_type': str}]
        
        Returns:
            dict: 발송 결과
        """
        try:
            if not self.api_key:
                return {
                    'success': False,
                    'error': 'SendGrid가 설정되지 않았습니다.'
                }
            
            # SendGrid 메일 객체 생성
            message = Mail(
                from_email=Email(self.from_email, self.from_name),
                to_emails=To(to_email),
                subject=subject,
                plain_text_content=Content("text/plain", content) if content_type == 'text/plain' else None,
                html_content=Content("text/html", content) if content_type == 'text/html' else None
            )
            
            # 첨부파일 추가
            if attachments:
                for attachment_data in attachments:
                    file_content = attachment_data.get('file_content')
                    filename = attachment_data.get('filename')
                    file_type = attachment_data.get('file_type') or 'application/octet-stream'
                    
                    if file_content and filename:
                        # Base64 인코딩
                        encoded_content = base64.b64encode(file_content).decode()
                        
                        attachment = Attachment(
                            file_content=encoded_content,
                            file_name=filename,
                            file_type=file_type,
                            disposition="attachment"
                        )
                        message.add_attachment(attachment)
            
            # SendGrid API 클라이언트
            sg = SendGridAPIClient(self.api_key)
            
            # 이메일 발송
            response = sg.send(message)
            
            if response.status_code in [200, 201, 202]:
                logger.info(f"이메일 발송 성공: {to_email}, 제목: {subject}")
                return {
                    'success': True,
                    'status_code': response.status_code,
                    'message_id': response.headers.get('X-Message-Id')
                }
            else:
                logger.error(f"이메일 발송 실패: {response.status_code}, {response.body}")
                return {
                    'success': False,
                    'error': f"발송 실패 (상태코드: {response.status_code})",
                    'detail': response.body
                }
                
        except Exception as e:
            logger.error(f"이메일 발송 중 오류: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def send_html_email(self, to_email, subject, html_content, text_content=None, attachments=None):
        """
        HTML 이메일 발송
        
        Args:
            to_email: 수신 이메일
            subject: 제목
            html_content: HTML 내용
            text_content: 텍스트 대체 내용 (선택)
            attachments: 첨부파일 리스트 [{'file_content': bytes, 'filename': str, 'file_type': str}]
        """
        try:
            if not self.api_key:
                return {
                    'success': False,
                    'error': 'SendGrid가 설정되지 않았습니다.'
                }
            
            # 텍스트 버전이 없으면 HTML에서 태그 제거
            if not text_content:
                import re
                text_content = re.sub('<[^<]+?>', '', html_content)
            
            message = Mail(
                from_email=Email(self.from_email, self.from_name),
                to_emails=To(to_email),
                subject=subject,
                plain_text_content=Content("text/plain", text_content),
                html_content=Content("text/html", html_content)
            )
            
            # 첨부파일 추가
            if attachments:
                for attachment_data in attachments:
                    file_content = attachment_data.get('file_content')
                    filename = attachment_data.get('filename')
                    file_type = attachment_data.get('file_type') or 'application/octet-stream'
                    
                    if file_content and filename:
                        # Base64 인코딩
                        encoded_content = base64.b64encode(file_content).decode()
                        
                        attachment = Attachment(
                            file_content=encoded_content,
                            file_name=filename,
                            file_type=file_type,
                            disposition="attachment"
                        )
                        message.add_attachment(attachment)
            
            sg = SendGridAPIClient(self.api_key)
            response = sg.send(message)
            
            if response.status_code in [200, 201, 202]:
                logger.info(f"HTML 이메일 발송 성공: {to_email}")
                return {
                    'success': True,
                    'status_code': response.status_code,
                    'message_id': response.headers.get('X-Message-Id')
                }
            else:
                logger.error(f"HTML 이메일 발송 실패: {response.status_code}")
                return {
                    'success': False,
                    'error': f"발송 실패 (상태코드: {response.status_code})",
                    'detail': response.body
                }
                
        except Exception as e:
            logger.error(f"HTML 이메일 발송 중 오류: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def send_template_email(self, to_email, template_id, dynamic_data):
        """
        SendGrid 템플릿 이메일 발송 (SendGrid에서 템플릿 관리하는 경우)
        
        Args:
            to_email: 수신 이메일
            template_id: SendGrid 템플릿 ID
            dynamic_data: 템플릿 변수 데이터
        """
        try:
            if not self.api_key:
                return {
                    'success': False,
                    'error': 'SendGrid가 설정되지 않았습니다.'
                }
            
            message = Mail(
                from_email=Email(self.from_email, self.from_name),
                to_emails=To(to_email)
            )
            
            message.template_id = template_id
            message.dynamic_template_data = dynamic_data
            
            sg = SendGridAPIClient(self.api_key)
            response = sg.send(message)
            
            if response.status_code in [200, 201, 202]:
                logger.info(f"템플릿 이메일 발송 성공: {to_email}")
                return {
                    'success': True,
                    'status_code': response.status_code,
                    'message_id': response.headers.get('X-Message-Id')
                }
            else:
                return {
                    'success': False,
                    'error': f"발송 실패 (상태코드: {response.status_code})"
                }
                
        except Exception as e:
            logger.error(f"템플릿 이메일 발송 중 오류: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }