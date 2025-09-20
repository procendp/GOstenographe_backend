from requests.models import Request

print('=== Request 데이터 확인 ===')
requests = Request.objects.all()[:10]
for r in requests:
    print(f'ID: {r.id}, Name: {r.name}, Estimated Price: {r.estimated_price}')

print(f'\n총 Request 개수: {Request.objects.count()}')