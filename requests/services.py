import os
import requests
import resend
from django.template import Template as DjangoTemplate, Context
from django.conf import settings

class MessageService:
    @staticmethod
    def replace_template_variables(template_content, context_data):
        """템플릿의 변수를 실제 데이터로 치환"""
        template = DjangoTemplate(template_content)
        context = Context(context_data)
        return template.render(context)

    @staticmethod
    def send_sms(phone_number, message):
        """네이버 클라우드 SMS API를 사용하여 SMS 발송"""
        url = "https://sens.apigw.ntruss.com/sms/v2/services/{serviceId}/messages"
        headers = {
            "Content-Type": "application/json",
            "x-ncp-apigw-timestamp": "",  # 현재 timestamp
            "x-ncp-iam-access-key": settings.NAVER_ACCESS_KEY,
            "x-ncp-apigw-signature-v2": "",  # signature 계산 필요
        }
        data = {
            "type": "SMS",
            "from": settings.SENDER_PHONE,
            "content": message,
            "messages": [{"to": phone_number}]
        }
        
        try:
            response = requests.post(url, headers=headers, json=data)
            return response.status_code == 202
        except Exception as e:
            print(f"SMS 발송 실패: {str(e)}")
            return False

    @staticmethod
    def send_email(to_email, subject, content):
        """Resend를 사용하여 이메일 발송"""
        try:
            resend.api_key = settings.RESEND_API_KEY

            from_name = getattr(settings, 'RESEND_FROM_NAME', '속기사무소 정')
            from_email = settings.DEFAULT_FROM_EMAIL
            from_address = f"{from_name} <{from_email}>"

            params = {
                "from": from_address,
                "to": [to_email],
                "subject": subject,
                "html": content
            }

            response = resend.Emails.send(params)
            return response and response.get('id')
        except Exception as e:
            print(f"이메일 발송 실패: {str(e)}")
            return False 