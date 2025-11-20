"""
Resend Email Service - Direct REST API Implementation
"""
import os
import logging
import base64
import json
from django.conf import settings
import urllib.request
import urllib.error

logger = logging.getLogger(__name__)


class ResendEmail:
    """Resend Email Service Class using Direct REST API"""

    RESEND_API_URL = "https://api.resend.com/emails"

    def __init__(self):
        self.api_key = getattr(settings, 'RESEND_API_KEY', os.getenv('RESEND_API_KEY'))
        self.from_email = getattr(settings, 'RESEND_FROM_EMAIL', os.getenv('RESEND_FROM_EMAIL', 'info@sokgijung.com'))
        self.reply_to_email = getattr(settings, 'RESEND_REPLY_TO_EMAIL', os.getenv('RESEND_REPLY_TO_EMAIL', 'sokgijung@gmail.com'))
        self.from_name = getattr(settings, 'RESEND_FROM_NAME', os.getenv('RESEND_FROM_NAME', '속기사무소 정'))

        if not self.api_key:
            logger.warning("Resend API key is not configured. Check .env file.")

    def _make_request(self, payload):
        """
        Make HTTP request to Resend API

        Args:
            payload: Request payload dictionary

        Returns:
            tuple: (success: bool, response_data: dict)
        """
        try:
            logger.info(f"Resend API 요청 시작:")
            logger.info(f"  - URL: {self.RESEND_API_URL}")
            logger.info(f"  - To: {payload.get('to')}")
            logger.info(f"  - Subject: {payload.get('subject')}")
            logger.info(f"  - Has attachments: {len(payload.get('attachments', []))} files")

            # urllib로 POST 요청
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                self.RESEND_API_URL,
                data=data,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                method='POST'
            )

            response = urllib.request.urlopen(req, timeout=30)
            response_data = json.loads(response.read().decode('utf-8'))

            logger.info(f"Resend API 성공: {response.status}")
            return True, response_data

        except urllib.error.HTTPError as e:
            error_detail = e.read().decode('utf-8')
            try:
                error_detail = json.loads(error_detail)
            except:
                pass
            logger.error(f"Resend API 실패:")
            logger.error(f"  - HTTP Status: {e.code}")
            logger.error(f"  - Response: {error_detail}")
            return False, {"status_code": e.code, "detail": error_detail}

        except Exception as e:
            logger.error(f"Resend API 요청 중 예외 발생:")
            logger.error(f"  - Exception Type: {type(e).__name__}")
            logger.error(f"  - Exception Message: {str(e)}")
            import traceback
            logger.error(f"  - Traceback: {traceback.format_exc()}")
            return False, {"error": str(e), "exception_type": type(e).__name__}

    def send_email(self, to_email, subject, content, content_type='text/plain', attachments=None):
        """
        Send email

        Args:
            to_email: Recipient email
            subject: Subject
            content: Content
            content_type: 'text/plain' or 'text/html'
            attachments: List of attachments [{'file_content': bytes, 'filename': str, 'file_type': str}]

        Returns:
            dict: Send result
        """
        try:
            if not self.api_key:
                return {
                    'success': False,
                    'error': 'Resend is not configured.'
                }

            # Build email payload
            from_address = f"{self.from_name} <{self.from_email}>"

            payload = {
                "from": from_address,
                "to": [to_email],
                "subject": subject,
                "reply_to": self.reply_to_email
            }

            # Add content based on type
            if content_type == 'text/html':
                payload["html"] = content
            else:
                payload["text"] = content

            # Add attachments
            if attachments:
                attachment_list = []
                for attachment_data in attachments:
                    file_content = attachment_data.get('file_content')
                    filename = attachment_data.get('filename')

                    if file_content and filename:
                        # Base64 encode
                        encoded_content = base64.b64encode(file_content).decode()

                        attachment_list.append({
                            "content": encoded_content,
                            "filename": filename
                        })

                if attachment_list:
                    payload["attachments"] = attachment_list

            # Send email via REST API
            success, response_data = self._make_request(payload)

            if success:
                logger.info(f"Email sent successfully: {to_email}, Subject: {subject}")
                return {
                    'success': True,
                    'message_id': response_data.get('id')
                }
            else:
                logger.error(f"Email send failed: {response_data}")
                return {
                    'success': False,
                    'error': 'Send failed',
                    'detail': response_data
                }

        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def send_html_email(self, to_email, subject, html_content, text_content=None, attachments=None):
        """
        Send HTML email

        Args:
            to_email: Recipient email
            subject: Subject
            html_content: HTML content
            text_content: Text alternative content (optional)
            attachments: List of attachments [{'file_content': bytes, 'filename': str, 'file_type': str}]
        """
        try:
            if not self.api_key:
                return {
                    'success': False,
                    'error': 'Resend is not configured.'
                }

            # Build email payload
            from_address = f"{self.from_name} <{self.from_email}>"

            payload = {
                "from": from_address,
                "to": [to_email],
                "subject": subject,
                "html": html_content,
                "reply_to": self.reply_to_email
            }

            # Add text version if provided
            if text_content:
                payload["text"] = text_content
            else:
                # Remove HTML tags for text version
                import re
                payload["text"] = re.sub('<[^<]+?>', '', html_content)

            # Add attachments
            if attachments:
                attachment_list = []
                for attachment_data in attachments:
                    file_content = attachment_data.get('file_content')
                    filename = attachment_data.get('filename')

                    if file_content and filename:
                        # Base64 encode
                        encoded_content = base64.b64encode(file_content).decode()

                        attachment_list.append({
                            "content": encoded_content,
                            "filename": filename
                        })

                if attachment_list:
                    payload["attachments"] = attachment_list

            # Send email via REST API
            success, response_data = self._make_request(payload)

            if success:
                logger.info(f"HTML email sent successfully: {to_email}")
                return {
                    'success': True,
                    'message_id': response_data.get('id')
                }
            else:
                logger.error(f"HTML email send failed: {response_data}")
                logger.error(f"  - Status Code: {response_data.get('status_code')}")
                logger.error(f"  - Detail: {response_data.get('detail')}")
                return {
                    'success': False,
                    'error': 'Send failed',
                    'detail': response_data
                }

        except Exception as e:
            logger.error(f"Error sending HTML email: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def send_template_email(self, to_email, template_id, dynamic_data):
        """
        Send template email (for future use with Resend templates)

        Args:
            to_email: Recipient email
            template_id: Template ID
            dynamic_data: Template variable data
        """
        logger.warning("Resend template feature is not yet implemented. Use send_html_email instead.")
        return {
            'success': False,
            'error': 'Template feature not yet implemented'
        }
