from requests.models import Request, File

print('=== Request 데이터 상세 확인 ===')
requests = Request.objects.all()[:5]
for r in requests:
    print(f'ID: {r.id}, Name: {r.name}, Estimated Price: {r.estimated_price}')
    print(f'  Created: {r.created_at}')
    print(f'  Files: {r.files.count()}개')
    for f in r.files.all():
        print(f'    - {f.original_name} (S3: {f.file})')
    print()

print(f'총 Request 개수: {Request.objects.count()}')