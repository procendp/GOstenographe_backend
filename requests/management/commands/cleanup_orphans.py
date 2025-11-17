"""
Django Management Command: 고아 파일 정리
사용법:
  python manage.py cleanup_orphans                    # 분석만 (삭제 안 함)
  python manage.py cleanup_orphans --dry-run          # 분석만 (명시적)
  python manage.py cleanup_orphans --clean-s3         # S3 고아 파일만 삭제
  python manage.py cleanup_orphans --clean-db         # PostgreSQL 고아 레코드만 삭제
  python manage.py cleanup_orphans --clean-orphans    # 진짜 고아 파일만 삭제
  python manage.py cleanup_orphans --clean-all        # 모두 삭제
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from requests.models import File
import boto3


class Command(BaseCommand):
    help = '고아 파일 분석 및 정리 (속기록 파일 자동 보호)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='분석만 수행 (삭제 안 함)',
        )
        parser.add_argument(
            '--clean-s3',
            action='store_true',
            help='S3에만 있는 고아 파일 삭제',
        )
        parser.add_argument(
            '--clean-db',
            action='store_true',
            help='PostgreSQL에만 있는 고아 레코드 삭제',
        )
        parser.add_argument(
            '--clean-orphans',
            action='store_true',
            help='진짜 고아 파일 삭제 (request도 없고 transcript_requests도 없음)',
        )
        parser.add_argument(
            '--clean-all',
            action='store_true',
            help='모든 고아 파일 삭제',
        )

    def handle(self, *args, **options):
        self.stdout.write("=" * 80)
        self.stdout.write(self.style.SUCCESS("🧹 고아 파일 정리"))
        self.stdout.write("=" * 80)

        # S3 클라이언트 초기화
        try:
            s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_S3_REGION_NAME
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ S3 연결 실패: {str(e)}"))
            return

        # 1. S3의 모든 파일 키 가져오기
        self.stdout.write("\n1️⃣ S3 파일 목록 조회 중...")
        s3_files = set()
        paginator = s3_client.get_paginator('list_objects_v2')

        try:
            for page in paginator.paginate(Bucket=settings.AWS_STORAGE_BUCKET_NAME):
                if 'Contents' in page:
                    for obj in page['Contents']:
                        s3_files.add(obj['Key'])
            self.stdout.write(self.style.SUCCESS(f"   ✅ S3 파일 수: {len(s3_files)}개"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"   ❌ S3 조회 실패: {str(e)}"))
            return

        # 2. PostgreSQL의 모든 파일 키 가져오기
        self.stdout.write("\n2️⃣ PostgreSQL 파일 목록 조회 중...")
        db_files = {}
        for f in File.objects.all():
            db_files[f.file] = f
        self.stdout.write(self.style.SUCCESS(f"   ✅ PostgreSQL 파일 수: {len(db_files)}개"))

        # 3. 고아 파일 찾기
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write("고아 파일 분석 결과")
        self.stdout.write("=" * 80)

        # 타입 A: S3에만 있는 파일
        orphan_s3 = s3_files - set(db_files.keys())
        self.stdout.write(f"\n📁 타입 A - S3에만 있는 파일: {len(orphan_s3)}개")
        if orphan_s3:
            for i, key in enumerate(list(orphan_s3)[:10], 1):
                self.stdout.write(f"   {i}. {key}")
            if len(orphan_s3) > 10:
                self.stdout.write(f"   ... 외 {len(orphan_s3) - 10}개")

        # 타입 B: PostgreSQL에만 있는 파일
        orphan_db = set(db_files.keys()) - s3_files
        self.stdout.write(f"\n💾 타입 B - PostgreSQL에만 있는 파일: {len(orphan_db)}개")
        if orphan_db:
            for i, key in enumerate(list(orphan_db)[:10], 1):
                file_obj = db_files[key]
                self.stdout.write(f"   {i}. ID: {file_obj.id}, Key: {key}")
            if len(orphan_db) > 10:
                self.stdout.write(f"   ... 외 {len(orphan_db) - 10}개")

        # 타입 C: 진짜 고아 파일 (is_orphan() 사용)
        all_files = File.objects.all()
        true_orphans = []
        for f in all_files:
            if f.is_orphan():
                true_orphans.append(f)

        self.stdout.write(f"\n🔗 타입 C - 진짜 고아 파일 (일반 첨부도 아니고 속기록도 아님): {len(true_orphans)}개")
        if true_orphans:
            for i, f in enumerate(true_orphans[:10], 1):
                self.stdout.write(f"   {i}. ID: {f.id}, 파일명: {f.original_name}")
                self.stdout.write(f"      S3 Key: {f.file}")
            if len(true_orphans) > 10:
                self.stdout.write(f"   ... 외 {len(true_orphans) - 10}개")

        # 4. 결과 요약
        total_orphans = len(orphan_s3) + len(orphan_db) + len(true_orphans)

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write("요약")
        self.stdout.write("=" * 80)

        if total_orphans == 0:
            self.stdout.write(self.style.SUCCESS("\n✅ 고아 파일이 없습니다! 깨끗한 상태입니다."))
            return

        self.stdout.write(self.style.WARNING(f"\n⚠️  총 {total_orphans}개의 고아 파일이 발견되었습니다."))

        # 5. 삭제 실행 (옵션에 따라)
        if options['dry_run'] or not any([options['clean_s3'], options['clean_db'],
                                          options['clean_orphans'], options['clean_all']]):
            self.stdout.write("\n📋 분석만 수행했습니다. 삭제하려면 다음 옵션을 사용하세요:")
            self.stdout.write("  --clean-s3         S3 고아 파일 삭제")
            self.stdout.write("  --clean-db         PostgreSQL 고아 레코드 삭제")
            self.stdout.write("  --clean-orphans    진짜 고아 파일 삭제")
            self.stdout.write("  --clean-all        모두 삭제")
            return

        # 삭제 실행
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write("삭제 실행")
        self.stdout.write("=" * 80)

        # 타입 A 삭제
        if options['clean_s3'] or options['clean_all']:
            self.stdout.write("\n🗑️  S3에서 고아 파일 삭제 중...")
            count = 0
            for key in orphan_s3:
                try:
                    s3_client.delete_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=key)
                    count += 1
                    self.stdout.write(self.style.SUCCESS(f"   ✅ 삭제: {key}"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"   ❌ 실패: {key} - {str(e)}"))
            self.stdout.write(self.style.SUCCESS(f"\n   총 {count}개 삭제 완료"))

        # 타입 B 삭제
        if options['clean_db'] or options['clean_all']:
            self.stdout.write("\n🗑️  PostgreSQL에서 고아 레코드 삭제 중...")
            count = 0
            for key in orphan_db:
                file_obj = db_files[key]
                try:
                    # S3 파일이 없으므로 DB만 삭제
                    File.objects.filter(id=file_obj.id).delete()
                    count += 1
                    self.stdout.write(self.style.SUCCESS(f"   ✅ 삭제: ID {file_obj.id} - {key}"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"   ❌ 실패: ID {file_obj.id} - {str(e)}"))
            self.stdout.write(self.style.SUCCESS(f"\n   총 {count}개 삭제 완료"))

        # 타입 C 삭제
        if options['clean_orphans'] or options['clean_all']:
            self.stdout.write("\n🗑️  진짜 고아 파일 레코드 삭제 중...")
            self.stdout.write(self.style.WARNING("   (속기록 완성 파일은 자동 보호됩니다)"))
            count = 0
            for f in true_orphans:
                try:
                    # is_orphan()으로 한번 더 확인 (안전장치)
                    if f.is_orphan():
                        f.delete()  # S3 파일도 함께 삭제
                        count += 1
                        self.stdout.write(self.style.SUCCESS(f"   ✅ 삭제: ID {f.id} - {f.original_name}"))
                    else:
                        self.stdout.write(self.style.WARNING(f"   ⚠️  건너뜀 (연결된 파일): ID {f.id} - {f.original_name}"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"   ❌ 실패: ID {f.id} - {str(e)}"))
            self.stdout.write(self.style.SUCCESS(f"\n   총 {count}개 삭제 완료"))

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("완료"))
        self.stdout.write("=" * 80)
