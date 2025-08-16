from django.core.management.base import BaseCommand
from django.utils import timezone
from requests.models import File
from django.conf import settings
import boto3
from datetime import datetime, timedelta, timezone as dt_timezone

class Command(BaseCommand):
    help = 'Delete orphan S3 files not registered in DB and older than 6 hours.'

    def handle(self, *args, **options):
        s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
        )
        bucket = settings.AWS_STORAGE_BUCKET_NAME
        # DB에 등록된 모든 S3 key set
        db_keys = set(File.objects.values_list('file', flat=True))
        # S3 버킷의 모든 파일 목록
        paginator = s3_client.get_paginator('list_objects_v2')
        deleted_count = 0
        now = datetime.now(dt_timezone.utc)
        for page in paginator.paginate(Bucket=bucket):
            for obj in page.get('Contents', []):
                key = obj['Key']
                last_modified = obj['LastModified']
                # 6시간 이상 지난 파일만 orphan 체크
                if key not in db_keys and (now - last_modified).total_seconds() > 21600:
                    s3_client.delete_object(Bucket=bucket, Key=key)
                    deleted_count += 1
                    self.stdout.write(self.style.WARNING(f'Orphan S3 file deleted: {key}'))
        self.stdout.write(self.style.SUCCESS(f'Total orphan S3 files deleted: {deleted_count}')) 