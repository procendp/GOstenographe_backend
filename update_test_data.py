from requests.models import Request

print('=== 테스트 데이터 업데이트 ===')
requests = Request.objects.all()

# 첫 번째 요청은 90,000원으로 설정
if requests.exists():
    first_request = requests.first()
    first_request.estimated_price = 90000
    first_request.save()
    print(f'ID {first_request.id}: {first_request.estimated_price}원으로 업데이트')

# 두 번째 요청은 120,000원으로 설정
if requests.count() > 1:
    second_request = requests[1]
    second_request.estimated_price = 120000
    second_request.save()
    print(f'ID {second_request.id}: {second_request.estimated_price}원으로 업데이트')

print('\n업데이트 완료! 엑셀 뷰에서 확인해주세요.')