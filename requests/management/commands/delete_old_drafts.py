from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from requests.models import Request

class Command(BaseCommand):
    help = 'Delete draft requests older than 6 hours.'

    def handle(self, *args, **options):
        threshold = timezone.now() - timedelta(hours=6)
        old_drafts = Request.objects.filter(status='draft', created_at__lt=threshold)
        count = old_drafts.count()
        old_drafts.delete()
        self.stdout.write(self.style.SUCCESS(f'Deleted {count} draft requests older than 6 hours.')) 