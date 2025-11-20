"""
Resend Email Service
"""
import os
import logging
import base64
import resend
from django.conf import settings

logger = logging.getLogger(__name__)


class ResendEmail:
    """Resend Email Service Class"""

    def __init__(self):
        self.api_key = getattr(settings, 'RESEND_API_KEY', os.getenv('RESEND_API_KEY'))
        self.from_email = getattr(settings, 'RESEND_FROM_EMAIL', os.getenv('RESEND_FROM_EMAIL', 'info@sokgijung.com'))
        self.reply_to_email = getattr(settings, 'RESEND_REPLY_TO_EMAIL', os.getenv('RESEND_REPLY_TO_EMAIL', 'sokgijung@gmail.com'))
        self.from_name = getattr(settings, 'RESEND_FROM_NAME', os.getenv('RESEND_FROM_NAME', '속기사무소 정'))

        if not self.api_key:
            logger.warning("Resend API key is not configured. Check .env file.")
        else:
            resend.api_key = self.api_key

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

            # Build email parameters
            from_address = f"{self.from_name} <{self.from_email}>"

            params = {
                "from": from_address,
                "to": [to_email],
                "subject": subject,
                "reply_to": self.reply_to_email
            }

            # Add content based on type
            if content_type == 'text/html':
                params["html"] = content
            else:
                params["text"] = content

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
                    params["attachments"] = attachment_list

            # Send email
            response = resend.Emails.send(params)

            if response and response.get('id'):
                logger.info(f"Email sent successfully: {to_email}, Subject: {subject}")
                return {
                    'success': True,
                    'message_id': response.get('id')
                }
            else:
                logger.error(f"Email send failed: {response}")
                return {
                    'success': False,
                    'error': 'Send failed',
                    'detail': str(response)
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

            # Build email parameters
            from_address = f"{self.from_name} <{self.from_email}>"

            params = {
                "from": from_address,
                "to": [to_email],
                "subject": subject,
                "html": html_content,
                "reply_to": self.reply_to_email
            }

            # Add text version if provided
            if text_content:
                params["text"] = text_content
            else:
                # Remove HTML tags for text version
                import re
                params["text"] = re.sub('<[^<]+?>', '', html_content)

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
                    params["attachments"] = attachment_list

            # Send email
            response = resend.Emails.send(params)

            if response and response.get('id'):
                logger.info(f"HTML email sent successfully: {to_email}")
                return {
                    'success': True,
                    'message_id': response.get('id')
                }
            else:
                logger.error(f"HTML email send failed: {response}")
                return {
                    'success': False,
                    'error': 'Send failed',
                    'detail': str(response)
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
