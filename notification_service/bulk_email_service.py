"""
대량 이메일 발송 및 파일 첨부 서비스
"""
import boto3
from django.conf import settings
from django.template.loader import render_to_string
from .email_sender import SendGridEmail
import mimetypes
import os
from requests.models import Request

class BulkEmailService:
    """같은 주문 건의 파일들을 묶어서 이메일 발송하는 서비스"""
    
    def __init__(self):
        self.email_sender = SendGridEmail()
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
        )
    
    def get_files_from_s3(self, file_keys):
        """
        S3에서 여러 파일을 다운로드
        
        Args:
            file_keys: S3 파일 키 리스트
            
        Returns:
            list: 파일 데이터 리스트 [{'file_content': bytes, 'filename': str, 'file_type': str}]
        """
        attachments = []
        
        for file_key in file_keys:
            if not file_key:
                continue
                
            try:
                # S3에서 파일 다운로드
                response = self.s3_client.get_object(
                    Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                    Key=file_key
                )
                
                file_content = response['Body'].read()
                filename = os.path.basename(file_key)
                file_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
                
                attachments.append({
                    'file_content': file_content,
                    'filename': filename,
                    'file_type': file_type
                })
                
            except Exception as e:
                print(f"[BulkEmailService] S3 파일 다운로드 실패: {file_key}, 오류: {str(e)}")
                continue
        
        return attachments
    
    def group_requests_by_email(self, requests):
        """
        요청들을 이메일 주소별로 그룹화
        
        Args:
            requests: Request 객체 리스트
            
        Returns:
            dict: {email: [request1, request2, ...]}
        """
        grouped = {}
        
        for request in requests:
            email = request.email
            if email not in grouped:
                grouped[email] = []
            grouped[email].append(request)
        
        return grouped
    
    def create_template_context(self, requests):
        """
        요청 데이터를 기반으로 이메일 템플릿 컨텍스트 생성
        
        Args:
            requests: Request 객체 리스트
            
        Returns:
            dict: 템플릿 컨텍스트 데이터
        """
        if not requests:
            return {}
        
        # 첫 번째 요청의 정보 사용 (같은 이메일이므로 고객 정보는 동일)
        first_request = requests[0]
        
        # 업로드된 파일 정보 수집 - 각 Request의 모든 파일들을 수집
        uploaded_files = []
        total_duration = 0
        
        for request in requests:
            # 각 Request의 모든 파일들을 개별적으로 처리
            if request.files.exists():
                file_count = request.files.count()
                request_duration = request.total_duration or '00:00:00'
                
                # Request의 총 duration을 초로 변환
                request_duration_seconds = 0
                if request_duration and request_duration != '00:00:00':
                    try:
                        parts = request_duration.split(':')
                        if len(parts) == 3:
                            request_duration_seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                    except (ValueError, IndexError):
                        pass
                
                # 각 파일별로 duration을 균등 분배
                file_duration_seconds = request_duration_seconds // file_count if file_count > 0 else 0
                file_duration_str = f"{file_duration_seconds // 3600:02d}:{(file_duration_seconds % 3600) // 60:02d}:{file_duration_seconds % 60:02d}"
                
                for file_obj in request.files.all():
                    # 각 파일의 원본 이름 사용
                    file_name = file_obj.original_name or os.path.basename(file_obj.file)
                    
                    uploaded_files.append({
                        'name': file_name,
                        'duration': file_duration_str
                    })
                    
                    total_duration += file_duration_seconds
            else:
                # 파일이 없는 경우 Request 정보만으로 생성
                file_name = f"속기록_{getattr(request, 'request_id', request.id)}"
                file_duration = request.total_duration or '00:00:00'
                
                # 지속시간을 초로 변환하여 합계 계산
                if file_duration and file_duration != '00:00:00':
                    try:
                        parts = file_duration.split(':')
                        if len(parts) == 3:
                            total_duration += int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                    except (ValueError, IndexError):
                        pass
                    
                uploaded_files.append({
                    'name': file_name,
                    'duration': file_duration
                })
        
        # 총 지속시간을 HH:MM:SS 형식으로 변환
        hours = total_duration // 3600
        minutes = (total_duration % 3600) // 60
        seconds = total_duration % 60
        total_duration_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
        # final_option을 사용자 친화적인 값으로 변환
        final_option_display = {
            'file': '파일',
            'file_usb': '파일+우편',
            'file_usb_cd': '파일+우편+CD',
            'file_usb_post': '파일+우편+USB'
        }.get(first_request.final_option, first_request.final_option)
        
        context = {
            'customer_name': first_request.name or '고객',
            'order_id': first_request.order_id or 'N/A',
            'phone': first_request.phone or '',
            'email': first_request.email or '',
            'address': first_request.address or '',
            'final_option': final_option_display,
            'file_summary': f"총 {len(uploaded_files)}개 파일 / {total_duration_str}",
            'uploaded_files': uploaded_files
        }
        
        return context
    
    def send_emails_with_template(self, requests, template_name='email_templates/Service application completion Guide/email template_Service application completion Guide/index.html', email_subject='서비스 신청 완료 안내'):
        """
        동적 템플릿을 사용하여 대량 이메일 발송
        
        Args:
            requests: Request 객체 리스트
            template_name: 이메일 템플릿 경로
            email_subject: 이메일 제목
            
        Returns:
            dict: 발송 결과
        """
        grouped_requests = self.group_requests_by_email(requests)
        success_count = 0
        failed_emails = []
        
        for email, email_requests in grouped_requests.items():
            try:
                # 템플릿 컨텍스트 생성
                context = self.create_template_context(email_requests)
                
                # 템플릿 렌더링
                email_content = render_to_string(template_name, context)
                
                # 파일 첨부 처리 (기존 로직 사용)
                file_keys = []
                for request in email_requests:
                    # 수정안 파일 수집
                    if hasattr(request, 'draft_file') and request.draft_file and request.draft_file.file:
                        file_keys.append(request.draft_file.file)
                    
                    # 속기록 파일 수집
                    if hasattr(request, 'transcript_file') and request.transcript_file and request.transcript_file.file:
                        file_keys.append(request.transcript_file.file)
                    
                    # 기타 첨부 파일들 수집
                    for file_obj in request.files.all():
                        if file_obj.file:
                            file_keys.append(file_obj.file)
                
                # 중복 파일 제거
                file_keys = list(set(file_keys))
                
                # 파일 크기 제한 체크 및 첨부파일 생성
                attachments = []
                total_size = 0
                
                for file_key in file_keys:
                    try:
                        # S3에서 파일 메타데이터 확인
                        head_response = self.s3_client.head_object(
                            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                            Key=file_key
                        )
                        file_size = head_response['ContentLength']
                        
                        if total_size + file_size > 25 * 1024 * 1024:  # 25MB 제한
                            print(f"[BulkEmailService] 파일 크기 제한 초과로 {file_key} 스킵")
                            continue
                        
                        total_size += file_size
                        
                        # 실제 파일 다운로드
                        response = self.s3_client.get_object(
                            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                            Key=file_key
                        )
                        
                        file_content = response['Body'].read()
                        filename = os.path.basename(file_key)
                        file_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
                        
                        # Request의 파일에서 원본 파일명 찾기
                        original_filename = filename
                        for request in email_requests:
                            for file_obj in request.files.all():
                                if file_obj.file == file_key:
                                    original_filename = file_obj.original_name or filename
                                    break
                        
                        attachments.append({
                            'file_content': file_content,
                            'filename': original_filename,
                            'file_type': file_type
                        })
                        
                    except Exception as e:
                        print(f"[BulkEmailService] 파일 처리 실패: {file_key}, 오류: {str(e)}")
                        continue
                
                # 이메일 발송
                result = self.email_sender.send_html_email(
                    to_email=email,
                    subject=email_subject,
                    html_content=email_content,
                    attachments=attachments
                )
                
                if result.get('success'):
                    success_count += 1
                    print(f"[BulkEmailService] 템플릿 이메일 발송 성공: {email}, 첨부파일 {len(attachments)}개")
                else:
                    failed_emails.append({
                        'email': email,
                        'error': result.get('error', '알 수 없는 오류')
                    })
                    print(f"[BulkEmailService] 템플릿 이메일 발송 실패: {email}, 오류: {result.get('error')}")
                    
            except Exception as e:
                failed_emails.append({
                    'email': email,
                    'error': str(e)
                })
                print(f"[BulkEmailService] 템플릿 이메일 처리 실패: {email}, 오류: {str(e)}")
        
        return {
            'success_count': success_count,
            'failed_emails': failed_emails,
            'total_emails': len(grouped_requests)
        }
    
    def send_bulk_emails_with_attachments(self, requests, email_subject, email_content, content_type='text/html'):
        """
        같은 이메일 주소를 가진 요청들의 파일을 모두 첨부하여 발송
        
        Args:
            requests: Request 객체 리스트
            email_subject: 이메일 제목
            email_content: 이메일 내용
            content_type: 'text/plain' 또는 'text/html'
            
        Returns:
            dict: 발송 결과 {'success_count': int, 'failed_emails': []}
        """
        grouped_requests = self.group_requests_by_email(requests)
        success_count = 0
        failed_emails = []
        
        for email, email_requests in grouped_requests.items():
            try:
                # 해당 이메일의 모든 요청에서 파일 수집
                file_keys = []
                
                for request in email_requests:
                    # 수정안 파일 수집
                    if hasattr(request, 'draft_file') and request.draft_file and request.draft_file.file:
                        file_keys.append(request.draft_file.file)
                    
                    # 속기록 파일 수집
                    if hasattr(request, 'transcript_file') and request.transcript_file and request.transcript_file.file:
                        file_keys.append(request.transcript_file.file)
                    
                    # 기타 첨부 파일들 수집
                    for file_obj in request.files.all():
                        if file_obj.file:
                            file_keys.append(file_obj.file)
                
                # 중복 파일 제거
                file_keys = list(set(file_keys))
                
                # 파일 크기 제한 체크 (최대 25MB, 여유분 두기)
                total_size = 0
                attachments = []
                
                for file_key in file_keys:
                    try:
                        # S3에서 파일 메타데이터만 가져와서 크기 확인
                        head_response = self.s3_client.head_object(
                            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                            Key=file_key
                        )
                        file_size = head_response['ContentLength']
                        
                        if total_size + file_size > 25 * 1024 * 1024:  # 25MB 제한
                            print(f"[BulkEmailService] 파일 크기 제한 초과로 {file_key} 스킵")
                            continue
                        
                        total_size += file_size
                        
                        # 실제 파일 다운로드
                        response = self.s3_client.get_object(
                            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                            Key=file_key
                        )
                        
                        file_content = response['Body'].read()
                        filename = os.path.basename(file_key)
                        file_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
                        
                        # Request의 파일에서 원본 파일명 찾기
                        original_filename = filename
                        for request in email_requests:
                            for file_obj in request.files.all():
                                if file_obj.file == file_key:
                                    original_filename = file_obj.original_name or filename
                                    break
                        
                        attachments.append({
                            'file_content': file_content,
                            'filename': original_filename,
                            'file_type': file_type
                        })
                        
                    except Exception as e:
                        print(f"[BulkEmailService] 파일 처리 실패: {file_key}, 오류: {str(e)}")
                        continue
                
                # 이메일 발송
                if content_type == 'text/html':
                    result = self.email_sender.send_html_email(
                        to_email=email,
                        subject=email_subject,
                        html_content=email_content,
                        attachments=attachments
                    )
                else:
                    result = self.email_sender.send_email(
                        to_email=email,
                        subject=email_subject,
                        content=email_content,
                        content_type=content_type,
                        attachments=attachments
                    )
                
                if result.get('success'):
                    success_count += 1
                    print(f"[BulkEmailService] 발송 성공: {email}, 첨부파일 {len(attachments)}개")
                else:
                    failed_emails.append({
                        'email': email,
                        'error': result.get('error', '알 수 없는 오류')
                    })
                    print(f"[BulkEmailService] 발송 실패: {email}, 오류: {result.get('error')}")
                    
            except Exception as e:
                failed_emails.append({
                    'email': email,
                    'error': str(e)
                })
                print(f"[BulkEmailService] 이메일 처리 실패: {email}, 오류: {str(e)}")
        
        return {
            'success_count': success_count,
            'failed_emails': failed_emails,
            'total_emails': len(grouped_requests)
        }