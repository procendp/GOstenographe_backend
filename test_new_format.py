from requests.models import Request

print('=== 새로운 Request ID 형식 테스트 (YYMMDD_ORDERIDNN) ===')

# 기존 데이터 삭제 (테스트용)
print('기존 테스트 데이터 삭제...')
Request.objects.filter(name__startswith='테스트').delete()

print('\n=== 새로운 Request 생성 테스트 ===')

# Order ID 1의 첫 번째 Request
test1 = Request(
    name='테스트 사용자1',
    email='test1@example.com',
    phone='010-1111-1111',
    estimated_price=75000
)
test1.save()
print(f'Order ID 1, 첫 번째: {test1.request_id} (Order ID: {test1.order_id})')

# Order ID 1의 두 번째 Request
test2 = Request(
    name='테스트 사용자1',
    email='test1@example.com',
    phone='010-1111-1111',
    estimated_price=80000,
    order_id=test1.order_id  # 같은 Order ID
)
test2.save()
print(f'Order ID 1, 두 번째: {test2.request_id} (Order ID: {test2.order_id})')

# Order ID 2의 첫 번째 Request
test3 = Request(
    name='테스트 사용자2',
    email='test2@example.com',
    phone='010-2222-2222',
    estimated_price=90000
)
test3.save()
print(f'Order ID 2, 첫 번째: {test3.request_id} (Order ID: {test3.order_id})')

# Order ID 2의 두 번째 Request
test4 = Request(
    name='테스트 사용자2',
    email='test2@example.com', 
    phone='010-2222-2222',
    estimated_price=95000,
    order_id=test3.order_id  # 같은 Order ID
)
test4.save()
print(f'Order ID 2, 두 번째: {test4.request_id} (Order ID: {test4.order_id})')

print('\n=== 큰 Order ID 테스트 (100 이상) ===')
# Order ID를 123으로 강제 설정하여 테스트
test5 = Request(
    name='테스트 사용자3',
    email='test3@example.com',
    phone='010-3333-3333',
    estimated_price=100000,
    order_id=123
)
test5.save()
print(f'Order ID 123, 첫 번째: {test5.request_id} (Order ID: {test5.order_id})')

test6 = Request(
    name='테스트 사용자3',
    email='test3@example.com',
    phone='010-3333-3333',
    estimated_price=105000,
    order_id=123
)
test6.save()
print(f'Order ID 123, 두 번째: {test6.request_id} (Order ID: {test6.order_id})')

print('\n완료!')