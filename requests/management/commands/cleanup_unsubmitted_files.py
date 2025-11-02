from django.core.management.base import BaseCommand
from django.utils import timezone
from requests.models import File
from django.conf import settings
import boto3
from datetime import timedelta

class Command(BaseCommand):
    help = 'Delete files uploaded but not submitted (no Request) after 6 hours'

    def handle(self, *args, **options):
        # 6시간 전 시간 계산
        cutoff_time = timezone.now() - timedelta(hours=6)

        # File은 있지만 Request가 없는 파일 (6시간 이상 된 것만)
        orphaned_files = File.objects.filter(
            created_at__lt=cutoff_time,
            request__isnull=True
        )

        if orphaned_files.count() == 0:
            self.stdout.write(self.style.SUCCESS('No orphaned files to clean up'))
            return

        # S3 클라이언트 초기화
        s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
        )
        bucket = settings.AWS_STORAGE_BUCKET_NAME

        deleted_count = 0
        failed_count = 0

        for file_obj in orphaned_files:
            try:
                # S3에서 파일 삭제
                s3_client.delete_object(Bucket=bucket, Key=file_obj.file)

                # DB에서 File 레코드 삭제
                file_name = file_obj.file_name
                file_obj.delete()

                deleted_count += 1
                self.stdout.write(
                    self.style.WARNING(
                        f'Deleted orphaned file: {file_name} '
                        f'(created: {file_obj.created_at})'
                    )
                )
            except Exception as e:
                failed_count += 1
                self.stdout.write(
                    self.style.ERROR(
                        f'Failed to delete file {file_obj.file}: {str(e)}'
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\nCleanup complete:\n'
                f'  - Deleted: {deleted_count} files\n'
                f'  - Failed: {failed_count} files'
            )
        )
