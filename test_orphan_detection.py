#!/usr/bin/env python
"""
고아 파일 판단 로직 테스트
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
os.environ['USE_PRODUCTION_DB'] = 'True'

django.setup()

from requests.models import Request, File

print("=" * 80)
print("🧪 고아 파일 판단 로직 테스트")
print("=" * 80)

# 모든 File 조회
files = File.objects.all()

if files.count() == 0:
    print("\n⚠️  파일이 하나도 없습니다. 데이터베이스가 비어있습니다.")
else:
    print(f"\n총 {files.count()}개의 파일을 분석합니다...\n")

    # 파일 타입별로 분류
    normal_files = []  # request와 연결된 일반 첨부 파일
    transcript_files = []  # transcript_requests로 연결된 속기록 파일
    orphan_files = []  # 진짜 고아 파일

    for f in files:
        # 일반 첨부 파일?
        if f.request is not None:
            normal_files.append(f)
        # 속기록 파일?
        elif f.transcript_requests.exists():
            transcript_files.append(f)
        # 고아 파일?
        elif f.is_orphan():
            orphan_files.append(f)

    # 결과 출력
    print("=" * 80)
    print("분석 결과")
    print("=" * 80)

    print(f"\n✅ 일반 첨부 파일 (File.request 연결): {len(normal_files)}개")
    if normal_files:
        for i, f in enumerate(normal_files[:5], 1):
            print(f"   {i}. ID: {f.id}, 파일명: {f.original_name}")
            print(f"      → Request ID: {f.request.request_id} ({f.request.name})")
        if len(normal_files) > 5:
            print(f"   ... 외 {len(normal_files) - 5}개")

    print(f"\n✅ 속기록 완성 파일 (transcript_requests 연결): {len(transcript_files)}개")
    if transcript_files:
        for i, f in enumerate(transcript_files[:5], 1):
            print(f"   {i}. ID: {f.id}, 파일명: {f.original_name}")
            # 어떤 Request의 속기록인지 확인
            for req in f.transcript_requests.all():
                print(f"      → Request ID: {req.request_id} ({req.name})의 속기록")
        if len(transcript_files) > 5:
            print(f"   ... 외 {len(transcript_files) - 5}개")

    print(f"\n⚠️  진짜 고아 파일 (삭제 가능): {len(orphan_files)}개")
    if orphan_files:
        for i, f in enumerate(orphan_files[:10], 1):
            print(f"   {i}. ID: {f.id}, 파일명: {f.original_name}")
            print(f"      S3 Key: {f.file}")
            print(f"      is_orphan(): {f.is_orphan()}")
        if len(orphan_files) > 10:
            print(f"   ... 외 {len(orphan_files) - 10}개")

    # 검증
    print("\n" + "=" * 80)
    print("검증")
    print("=" * 80)

    total = len(normal_files) + len(transcript_files) + len(orphan_files)
    print(f"\n총합: {total}개 (전체 파일: {files.count()}개)")

    if total == files.count():
        print("✅ 모든 파일이 정확히 분류되었습니다!")
    else:
        print(f"⚠️  {files.count() - total}개의 파일이 누락되었습니다. 로직 확인 필요!")

print("\n" + "=" * 80)
print("테스트 완료")
print("=" * 80)
