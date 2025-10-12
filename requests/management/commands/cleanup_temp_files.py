from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from requests.models import Request, File
import boto3
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '24시간 이상 경과한 임시 파일 및 Request 삭제'

    def add_arguments(self, parser):
        parser.add_argument(
            '--hours',
            type=int,
            default=24,
            help='삭제할 파일의 최소 경과 시간 (기본: 24시간)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='실제로 삭제하지 않고 삭제 대상만 확인'
        )

    def handle(self, *args, **options):
        hours = options['hours']
        dry_run = options['dry_run']
        
        cutoff_time = timezone.now() - timedelta(hours=hours)
        
        self.stdout.write(self.style.WARNING(f'\n{"=" * 60}'))
        self.stdout.write(self.style.WARNING(f'임시 파일 정리 시작 (기준: {hours}시간 전)'))
        self.stdout.write(self.style.WARNING(f'기준 시간: {cutoff_time}'))
        if dry_run:
            self.stdout.write(self.style.WARNING('*** DRY RUN 모드 (실제 삭제 안함) ***'))
        self.stdout.write(self.style.WARNING(f'{"=" * 60}\n'))

        # 임시 Request 찾기 (is_temporary=True이고 24시간 이상 경과)
        temp_requests = Request.objects.filter(
            is_temporary=True,
            created_at__lt=cutoff_time
        )

        total_requests = temp_requests.count()
        total_files = 0
        deleted_files = 0
        failed_files = 0

        self.stdout.write(f'발견된 임시 Request: {total_requests}개\n')

        if total_requests == 0:
            self.stdout.write(self.style.SUCCESS('삭제할 임시 Request가 없습니다.'))
            return

        # S3 클라이언트 생성
        try:
            s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_S3_REGION_NAME
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'S3 클라이언트 생성 실패: {str(e)}'))
            return

        # 각 임시 Request 처리
        for request_obj in temp_requests:
            self.stdout.write(f'\n처리 중: Request ID {request_obj.request_id} (생성: {request_obj.created_at})')
            
            # 첨부 파일 삭제
            files = request_obj.files.all()
            for file_obj in files:
                total_files += 1
                self.stdout.write(f'  - 파일: {file_obj.original_name} ({file_obj.file})')
                
                if not dry_run:
                    try:
                        # S3에서 삭제
                        s3_client.delete_object(
                            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                            Key=file_obj.file
                        )
                        deleted_files += 1
                        self.stdout.write(self.style.SUCCESS(f'    ✓ S3 삭제 성공'))
                    except Exception as e:
                        failed_files += 1
                        self.stdout.write(self.style.ERROR(f'    ✗ S3 삭제 실패: {str(e)}'))
            
            # 속기록 파일 삭제
            if request_obj.transcript_file:
                total_files += 1
                self.stdout.write(f'  - 속기록: {request_obj.transcript_file.original_name}')
                
                if not dry_run:
                    try:
                        s3_client.delete_object(
                            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                            Key=request_obj.transcript_file.file
                        )
                        deleted_files += 1
                        self.stdout.write(self.style.SUCCESS(f'    ✓ S3 삭제 성공'))
                    except Exception as e:
                        failed_files += 1
                        self.stdout.write(self.style.ERROR(f'    ✗ S3 삭제 실패: {str(e)}'))
            
            # Request 삭제 (CASCADE로 File도 자동 삭제)
            if not dry_run:
                request_obj.delete()
                self.stdout.write(self.style.SUCCESS(f'  ✓ Request 삭제 완료'))

        # 최종 결과
        self.stdout.write(self.style.WARNING(f'\n{"=" * 60}'))
        self.stdout.write(self.style.WARNING('정리 완료'))
        self.stdout.write(self.style.WARNING(f'{"=" * 60}'))
        
        if dry_run:
            self.stdout.write(f'삭제 대상 Request: {total_requests}개')
            self.stdout.write(f'삭제 대상 파일: {total_files}개')
        else:
            self.stdout.write(self.style.SUCCESS(f'삭제된 Request: {total_requests}개'))
            self.stdout.write(self.style.SUCCESS(f'삭제된 파일: {deleted_files}개'))
            if failed_files > 0:
                self.stdout.write(self.style.ERROR(f'삭제 실패 파일: {failed_files}개'))
        
        self.stdout.write('')

