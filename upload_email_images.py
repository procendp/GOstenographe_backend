"""
이메일 템플릿 이미지를 S3에 업로드하는 스크립트
"""
import os
import boto3
from pathlib import Path
import mimetypes
from django.conf import settings

# Django 설정 초기화
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

def find_and_upload_img_folders(s3_client, path, template_base):
    """재귀적으로 img 폴더를 찾아서 업로드"""
    for item in path.iterdir():
        if item.is_dir():
            if item.name == 'img':
                # img 폴더의 모든 이미지 파일 업로드
                for img_file in item.iterdir():
                    if img_file.is_file():
                        # S3 키 생성 (폴더 구조 유지)
                        relative_path = img_file.relative_to(template_base)
                        s3_key = str(relative_path).replace('\\', '/')

                        # MIME 타입 추출
                        content_type, _ = mimetypes.guess_type(str(img_file))
                        if not content_type:
                            if img_file.suffix.lower() in ['.jpg', '.jpeg']:
                                content_type = 'image/jpeg'
                            elif img_file.suffix.lower() == '.png':
                                content_type = 'image/png'
                            else:
                                content_type = 'application/octet-stream'

                        try:
                            # 파일 읽기
                            with open(img_file, 'rb') as f:
                                file_content = f.read()

                            # S3에 업로드
                            s3_client.put_object(
                                Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                                Key=s3_key,
                                Body=file_content,
                                ContentType=content_type
                            )

                            # 업로드된 URL 출력
                            s3_url = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/{s3_key}"
                            print(f"✅ 업로드 완료: {img_file.name}")
                            print(f"   URL: {s3_url}")

                        except Exception as e:
                            print(f"❌ 업로드 실패: {img_file.name}")
                            print(f"   오류: {str(e)}")
            else:
                # 하위 폴더 재귀 탐색
                find_and_upload_img_folders(s3_client, item, template_base)

def upload_images_to_s3():
    """이메일 템플릿 이미지를 S3에 업로드"""

    # S3 클라이언트 초기화
    s3_client = boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME
    )

    # 템플릿 디렉토리 경로
    template_base = Path('templates')
    email_templates = template_base / 'email_templates'

    # 모든 템플릿 폴더를 재귀적으로 순회
    find_and_upload_img_folders(s3_client, email_templates, template_base)

if __name__ == "__main__":
    print("=== 이메일 템플릿 이미지 S3 업로드 시작 ===")
    upload_images_to_s3()
    print("\n=== 업로드 완료 ===")