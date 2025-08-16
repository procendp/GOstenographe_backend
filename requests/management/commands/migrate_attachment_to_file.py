from django.core.management.base import BaseCommand
from requests.models import Request, File
from django.utils import timezone

class Command(BaseCommand):
    help = 'Migrate Request.attachment files to File model'

    def handle(self, *args, **options):
        migrated = 0
        for req in Request.objects.exclude(attachment='').exclude(attachment__isnull=True):
            if req.attachment:
                File.objects.create(
                    request=req,
                    file=req.attachment,
                    uploaded_at=req.created_at if req.created_at else timezone.now()
                )
                migrated += 1
        self.stdout.write(self.style.SUCCESS(f'Migrated {migrated} files from Request.attachment to File model.')) 