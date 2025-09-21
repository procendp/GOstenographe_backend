#!/usr/bin/env python
"""
기본 알림 템플릿 생성 스크립트
Django 환경에서 실행: python manage.py shell < create_templates.py
"""
import os
import django

# Django 환경 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from requests.models import Template

def create_sample_templates():
    """기본 템플릿들 생성"""
    
    templates = [
        # 접수완료 템플릿
        {
            'name': 'received_sms',
            'type': 'sms',
            'content': '안녕하세요 {name}님, 고스테노그라피입니다.\n주문번호 {order_id}번 접수가 완료되었습니다.\n\n입금 확인 후 작업을 시작하겠습니다.\n감사합니다.'
        },
        {
            'name': 'received_email',
            'type': 'email',
            'content': '''안녕하세요 {name}님,

고스테노그라피입니다.

주문번호 {order_id}번 접수가 완료되었습니다.

▶ 주문 정보
- 주문번호: {order_id}
- 접수일시: {today}
- 녹음일시: {recording_date}
- 화자 수: {speaker_count}명
- 예상 견적: {estimated_price}
- 원고 형식: {draft_format}
- 최종 옵션: {final_option}

입금 확인 후 작업을 시작하겠습니다.

감사합니다.

--
{company}
전화: {company_phone}
이메일: {company_email}'''
        },
        
        # 결제완료 템플릿
        {
            'name': 'payment_completed_sms',
            'type': 'sms',
            'content': '{name}님, 결제가 완료되었습니다.\n곧 속기 작업을 시작하겠습니다.\n작업 시작시 다시 안내드리겠습니다.\n\n- {company}'
        },
        {
            'name': 'payment_completed_email',
            'type': 'email',
            'content': '''안녕하세요 {name}님,

결제가 완료되어 안내드립니다.

▶ 결제 정보
- 주문번호: {order_id}
- 결제금액: {payment_amount}
- 결제상태: {payment_status}

곧 속기 작업을 시작하겠습니다.
작업 시작시 다시 안내드리겠습니다.

감사합니다.

--
{company}
전화: {company_phone}
이메일: {company_email}'''
        },
        
        # 작업시작 템플릿
        {
            'name': 'in_progress_email',
            'type': 'email',
            'content': '''안녕하세요 {name}님,

주문번호 {order_id}번의 속기 작업을 시작했습니다.

▶ 작업 정보
- 주문번호: {order_id}
- 녹음일시: {recording_date}
- 화자 수: {speaker_count}명
- 예상 소요시간: 영업일 기준 2-3일

작업 완료시 다시 안내드리겠습니다.

감사합니다.

--
{company}
전화: {company_phone}
이메일: {company_email}'''
        },
        
        # 작업완료 템플릿
        {
            'name': 'work_completed_sms',
            'type': 'sms',
            'content': '{name}님, 주문번호 {order_id}번 속기 작업이 완료되었습니다.\n최종 검토 후 발송하겠습니다.\n\n- {company}'
        },
        {
            'name': 'work_completed_email',
            'type': 'email',
            'content': '''안녕하세요 {name}님,

주문번호 {order_id}번의 속기 작업이 완료되었습니다.

▶ 작업 완료 정보
- 주문번호: {order_id}
- 작업완료일: {today}
- 최종 옵션: {final_option}

최종 검토 후 곧 발송하겠습니다.

감사합니다.

--
{company}
전화: {company_phone}
이메일: {company_email}'''
        },
        
        # 발송완료 템플릿
        {
            'name': 'sent_sms',
            'type': 'sms',
            'content': '{name}님, 주문번호 {order_id}번 속기록이 발송되었습니다.\n이메일을 확인해주세요.\n\n이용해주셔서 감사합니다.\n- {company}'
        },
        {
            'name': 'sent_email',
            'type': 'email',
            'content': '''안녕하세요 {name}님,

주문번호 {order_id}번의 속기록을 발송했습니다.

▶ 발송 정보
- 주문번호: {order_id}
- 발송일시: {today} {now}
- 최종 옵션: {final_option}

첨부파일을 확인해주세요.

속기 서비스를 이용해주셔서 감사합니다.
앞으로도 좋은 서비스로 보답하겠습니다.

--
{company}
전화: {company_phone}
이메일: {company_email}'''
        },
        
        # 취소 템플릿
        {
            'name': 'cancelled_sms',
            'type': 'sms',
            'content': '{name}님, 주문번호 {order_id}번이 취소되었습니다.\n환불 절차가 필요하시면 연락주세요.\n\n- {company}'
        },
        {
            'name': 'cancelled_email',
            'type': 'email',
            'content': '''안녕하세요 {name}님,

주문번호 {order_id}번이 취소되었습니다.

▶ 취소 정보
- 주문번호: {order_id}
- 취소일시: {today}

환불이 필요하시면 고객센터로 연락주세요.

감사합니다.

--
{company}
전화: {company_phone}
이메일: {company_email}'''
        },
        
        # 환불완료 템플릿
        {
            'name': 'refunded_sms',
            'type': 'sms',
            'content': '{name}님, 주문번호 {order_id}번 환불이 완료되었습니다.\n환불금액: {refund_amount}\n\n- {company}'
        },
        {
            'name': 'refunded_email',
            'type': 'email',
            'content': '''안녕하세요 {name}님,

주문번호 {order_id}번의 환불이 완료되었습니다.

▶ 환불 정보
- 주문번호: {order_id}
- 환불금액: {refund_amount}
- 환불일시: {today}

이용에 불편을 드려 죄송합니다.
앞으로 더 나은 서비스로 찾아뵙겠습니다.

감사합니다.

--
{company}
전화: {company_phone}
이메일: {company_email}'''
        },
        
        # 작업불가 템플릿
        {
            'name': 'impossible_sms',
            'type': 'sms',
            'content': '{name}님, 주문번호 {order_id}번 작업이 어려운 상황입니다.\n자세한 내용은 이메일을 확인해주세요.\n\n- {company}'
        },
        {
            'name': 'impossible_email',
            'type': 'email',
            'content': '''안녕하세요 {name}님,

주문번호 {order_id}번의 작업이 어려운 상황이 발생했습니다.

안타깝게도 현재 상황으로는 속기 작업이 어려울 것 같습니다.
자세한 사유 및 대안에 대해 전화로 상담드리겠습니다.

불편을 드려 죄송합니다.

--
{company}
전화: {company_phone}
이메일: {company_email}'''
        }
    ]
    
    created_count = 0
    updated_count = 0
    
    for template_data in templates:
        template, created = Template.objects.get_or_create(
            name=template_data['name'],
            type=template_data['type'],
            defaults={'content': template_data['content']}
        )
        
        if created:
            created_count += 1
            print(f"✓ 템플릿 생성: {template_data['name']}")
        else:
            # 기존 템플릿이 있으면 내용 업데이트
            template.content = template_data['content']
            template.save()
            updated_count += 1
            print(f"↻ 템플릿 업데이트: {template_data['name']}")
    
    print(f"\n템플릿 생성 완료!")
    print(f"- 새로 생성: {created_count}개")
    print(f"- 업데이트: {updated_count}개")
    print(f"- 총 템플릿: {Template.objects.count()}개")

if __name__ == '__main__':
    create_sample_templates()