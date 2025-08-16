from django.core.management.base import BaseCommand
import boto3
from django.conf import settings
from requests.models import S3File, RequestFile
from datetime import datetime

class Command(BaseCommand):
    help = 'S3 버킷의 파일 목록을 DB와 동기화합니다.'

    def handle(self, *args, **options):
        s3_client = boto3.client('s3')
        bucket_name = settings.AWS_STORAGE_BUCKET_NAME
        
        # S3의 모든 파일 목록 가져오기
        paginator = s3_client.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=bucket_name):
            if 'Contents' not in page:
                continue
                
            for obj in page['Contents']:
                file_key = obj['Key']
                file_size = obj['Size']
                last_modified = obj['LastModified']
                
                # DB에 이미 존재하는지 확인
                s3_file, created = S3File.objects.get_or_create(
                    file_key=file_key,
                    defaults={
                        'file_name': file_key.split('_', 1)[1] if '_' in file_key else file_key,
                        'file_size': file_size,
                        'uploaded_at': last_modified,
                    }
                )
                
                # RequestFile과 연결 확인
                if not s3_file.is_registered:
                    try:
                        request_file = RequestFile.objects.get(file_key=file_key)
                        s3_file.is_registered = True
                        s3_file.request = request_file.request
                        s3_file.save()
                    except RequestFile.DoesNotExist:
                        pass
                
                if created:
                    self.stdout.write(self.style.SUCCESS(f'새로운 파일 추가됨: {file_key}'))
                else:
                    self.stdout.write(self.style.SUCCESS(f'파일 업데이트됨: {file_key}'))
        
        self.stdout.write(self.style.SUCCESS('S3 파일 동기화가 완료되었습니다.')) 