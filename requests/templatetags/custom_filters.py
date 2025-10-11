from django import template
import re

register = template.Library()

@register.filter(name='format_phone')
def format_phone(value):
    """
    전화번호를 010-1234-5678 형식으로 포맷팅
    """
    if not value:
        return value
    
    # 숫자만 추출
    numbers = re.sub(r'[^0-9]', '', str(value))
    
    # 010으로 시작하는 11자리 번호인 경우
    if len(numbers) == 11 and numbers.startswith('010'):
        return f"{numbers[:3]}-{numbers[3:7]}-{numbers[7:]}"
    
    # 지역번호 포함 10자리 번호인 경우 (02-1234-5678)
    elif len(numbers) == 10:
        if numbers.startswith('02'):
            return f"{numbers[:2]}-{numbers[2:6]}-{numbers[6:]}"
        else:
            return f"{numbers[:3]}-{numbers[3:6]}-{numbers[6:]}"
    
    # 지역번호 포함 9자리 번호인 경우 (02-123-4567)
    elif len(numbers) == 9 and numbers.startswith('02'):
        return f"{numbers[:2]}-{numbers[2:5]}-{numbers[5:]}"
    
    # 그 외의 경우 원본 반환
    return value

