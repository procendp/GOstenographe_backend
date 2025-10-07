import boto3
from botocore.config import Config
from django.conf import settings
import uuid
import os

def generate_presigned_url(file_name, file_type, s3_key=None):
    """
    S3 Presigned URL을 생성합니다.
    
    Args:
        file_name (str): 원본 파일 이름
        file_type (str): 파일 MIME 타입
        s3_key (str): 기존에 있는 파일의 키
    
    Returns:
        dict: presigned URL과 파일 키를 포함한 딕셔너리
    """
    s3_client = boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME,
        config=Config(signature_version='s3v4')
    )
    
    # 파일 확장자 추출
    file_extension = file_name.split('.')[-1] if '.' in file_name else ''
    # 파일명에서 경로 제거 (보안)
    base_file_name = os.path.basename(file_name)
    # s3_key가 있으면 그걸 사용, 없으면 uuid 기반
    file_key = s3_key if s3_key else f'{uuid.uuid4()}.{file_extension}'
    
    # Presigned URL 생성
    presigned_url = s3_client.generate_presigned_url(
        'put_object',
        Params={
            'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
            'Key': file_key,
            'ContentType': file_type
        },
        ExpiresIn=3600  # URL 유효 시간 (1시간)
    )
    
    return {
        'upload_url': presigned_url,
        'file_key': file_key
    }

def validate_file_size(file_size):
    """
    파일 크기가 제한을 초과하는지 확인합니다.

    Args:
        file_size (int): 파일 크기 (bytes)

    Returns:
        bool: 파일 크기가 유효한지 여부
    """
    max_size = 500 * 1024 * 1024  # 500MB in bytes (한글/워드/텍스트 파일 용도)
    return file_size <= max_size 