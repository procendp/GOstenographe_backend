from django.core.management.base import BaseCommand
from django.utils import timezone
from requests.models import Request
from datetime import timedelta

class Command(BaseCommand):
    help = '1시간 이상 지난 임시 신청서와 연관 파일을 DB와 S3에서 모두 삭제합니다.'

    def handle(self, *args, **options):
        now = timezone.now()
        threshold = now - timedelta(hours=1)
        qs = Request.objects.filter(is_temporary=True, created_at__lt=threshold)
        count = qs.count()
        if count == 0:
            self.stdout.write(self.style.SUCCESS('No temporary requests to delete.'))
            return

        for req in qs:
            files = req.files.all()
            for f in files:
                try:
                    f.delete()  # File 모델의 delete가 S3까지 삭제
                    self.stdout.write(self.style.SUCCESS(f'Deleted file: {f.file.name}'))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Failed to delete file: {f.file.name} ({e})'))
            req.delete()
            self.stdout.write(self.style.SUCCESS(f'Deleted temporary request: {req.id}'))
        self.stdout.write(self.style.SUCCESS(f'Done. Deleted {count} temporary requests and their files.')) 