"""
Resend Email Service - Direct REST API Implementation
"""
import os
import logging
import base64
import json
from django.conf import settings
import importlib.util
import sys

# HTTP requests 라이브러리 직접 로드 (Django 앱 충돌 완전 회피)
spec = importlib.util.find_spec("requests")
http_lib = importlib.util.module_from_spec(spec)
spec.loader.exec_module(http_lib)

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
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            response = http_lib.post(
                self.RESEND_API_URL,
                headers=headers,
                data=json.dumps(payload),
                timeout=30
            )

            if response.status_code in [200, 201]:
                return True, response.json()
            else:
                error_detail = response.text
                try:
                    error_detail = response.json()
                except:
                    pass
                return False, {"status_code": response.status_code, "detail": error_detail}

        except Exception as e:
            return False, {"error": str(e)}

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
