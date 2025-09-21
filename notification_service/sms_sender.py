"""
Naver Cloud Platform SMS 발송 서비스
"""
import os
import hashlib
import hmac
import base64
import time
import json
import requests
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class NaverCloudSMS:
    """네이버 클라우드 플랫폼 SMS 발송 클래스"""
    
    def __init__(self):
        self.access_key = os.getenv('NCP_ACCESS_KEY')
        self.secret_key = os.getenv('NCP_SECRET_KEY')
        self.service_id = os.getenv('NCP_SMS_SERVICE_ID')
        self.from_number = os.getenv('NCP_SMS_FROM_NUMBER')
        
        if not all([self.access_key, self.secret_key, self.service_id, self.from_number]):
            logger.warning("NCP SMS 설정이 완료되지 않았습니다. .env 파일을 확인하세요.")
    
    def _make_signature(self, timestamp, uri, method="POST"):
        """NCP API 서명 생성"""
        message = f"{method} {uri}\n{timestamp}\n{self.access_key}"
        message = bytes(message, 'UTF-8')
        secret_key = bytes(self.secret_key, 'UTF-8')
        signature = base64.b64encode(hmac.new(secret_key, message, digestmod=hashlib.sha256).digest())
        return signature.decode('UTF-8')
    
    def send_sms(self, to_number, content):
        """
        SMS 발송
        
        Args:
            to_number: 수신번호 (01012345678 형식)
            content: 메시지 내용
        
        Returns:
            dict: 발송 결과
        """
        try:
            # API 설정 확인
            if not all([self.access_key, self.secret_key, self.service_id]):
                return {
                    'success': False,
                    'error': 'SMS 서비스가 설정되지 않았습니다.'
                }
            
            # 전화번호 포맷 정리 (하이픈 제거)
            to_number = to_number.replace('-', '').replace(' ', '')
            
            # NCP SMS API 엔드포인트
            uri = f"/sms/v2/services/{self.service_id}/messages"
            api_url = f"https://sens.apigw.ntruss.com{uri}"
            
            # 타임스탬프 생성
            timestamp = str(int(time.time() * 1000))
            
            # 헤더 설정
            headers = {
                'Content-Type': 'application/json; charset=utf-8',
                'x-ncp-apigw-timestamp': timestamp,
                'x-ncp-iam-access-key': self.access_key,
                'x-ncp-apigw-signature-v2': self._make_signature(timestamp, uri)
            }
            
            # 요청 본문
            body = {
                "type": "SMS",
                "from": self.from_number,
                "subject": "속기사무소 정",  # LMS일 때만 사용
                "content": content,
                "messages": [
                    {
                        "to": to_number,
                        "content": content
                    }
                ]
            }
            
            # API 호출
            response = requests.post(api_url, headers=headers, data=json.dumps(body))
            
            if response.status_code == 202:
                result_data = response.json()
                logger.info(f"SMS 발송 성공: {to_number}, Request ID: {result_data.get('requestId')}")
                return {
                    'success': True,
                    'request_id': result_data.get('requestId'),
                    'request_time': result_data.get('requestTime')
                }
            else:
                logger.error(f"SMS 발송 실패: {response.status_code}, {response.text}")
                return {
                    'success': False,
                    'error': f"발송 실패 (상태코드: {response.status_code})",
                    'detail': response.text
                }
                
        except Exception as e:
            logger.error(f"SMS 발송 중 오류: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def send_lms(self, to_number, subject, content):
        """
        LMS (장문 메시지) 발송
        
        Args:
            to_number: 수신번호
            subject: 제목
            content: 메시지 내용 (2000자 이내)
        """
        try:
            if not all([self.access_key, self.secret_key, self.service_id]):
                return {
                    'success': False,
                    'error': 'SMS 서비스가 설정되지 않았습니다.'
                }
            
            to_number = to_number.replace('-', '').replace(' ', '')
            
            uri = f"/sms/v2/services/{self.service_id}/messages"
            api_url = f"https://sens.apigw.ntruss.com{uri}"
            
            timestamp = str(int(time.time() * 1000))
            
            headers = {
                'Content-Type': 'application/json; charset=utf-8',
                'x-ncp-apigw-timestamp': timestamp,
                'x-ncp-iam-access-key': self.access_key,
                'x-ncp-apigw-signature-v2': self._make_signature(timestamp, uri)
            }
            
            body = {
                "type": "LMS",  # 장문 메시지
                "from": self.from_number,
                "subject": subject,
                "content": content,
                "messages": [
                    {
                        "to": to_number,
                        "subject": subject,
                        "content": content
                    }
                ]
            }
            
            response = requests.post(api_url, headers=headers, data=json.dumps(body))
            
            if response.status_code == 202:
                result_data = response.json()
                logger.info(f"LMS 발송 성공: {to_number}")
                return {
                    'success': True,
                    'request_id': result_data.get('requestId'),
                    'request_time': result_data.get('requestTime')
                }
            else:
                logger.error(f"LMS 발송 실패: {response.status_code}, {response.text}")
                return {
                    'success': False,
                    'error': f"발송 실패 (상태코드: {response.status_code})",
                    'detail': response.text
                }
                
        except Exception as e:
            logger.error(f"LMS 발송 중 오류: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }