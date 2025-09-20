from requests.models import Request

print('=== 기존 Request ID 형식 확인 ===')
requests = Request.objects.all()
for r in requests:
    print(f'ID: {r.id}, Order ID: {r.order_id}, Request ID: {r.request_id}')

print('\n=== 새로운 Request ID 형식으로 업데이트 ===')
for r in requests:
    old_request_id = r.request_id
    # save()를 호출하면 새로운 형식으로 Request ID가 생성됨
    r.save()
    print(f'ID: {r.id}, Order ID: {r.order_id}')
    print(f'  변경: {old_request_id} → {r.request_id}')

print('\n=== 새로운 Request 생성 테스트 ===')
# 새로운 Request를 생성해서 형식 확인
test_request = Request(
    name='테스트 사용자',
    email='test@example.com',
    phone='010-1234-5678',
    estimated_price=75000
)
test_request.save()
print(f'새로운 Request - Order ID: {test_request.order_id}, Request ID: {test_request.request_id}')

# 같은 Order ID로 두 번째 Request 생성
test_request2 = Request(
    name='테스트 사용자2',
    email='test2@example.com', 
    phone='010-1234-5679',
    estimated_price=80000,
    order_id=test_request.order_id  # 같은 Order ID 사용
)
test_request2.save()
print(f'같은 Order ID Request - Order ID: {test_request2.order_id}, Request ID: {test_request2.request_id}')

print('\n완료!')