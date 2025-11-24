"""
SMS 템플릿 생성 관리 명령어
사용법: python manage.py create_sms_templates
"""
from django.core.management.base import BaseCommand
from requests.models import Template


class Command(BaseCommand):
    help = 'SMS 템플릿 4개 생성 (기존 SMS 템플릿 전부 삭제 후 재생성)'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🚀 SMS 템플릿 생성 시작'))

        # 기존 SMS 템플릿 전부 삭제
        deleted_count = Template.objects.filter(type='sms').delete()[0]
        self.stdout.write(f'기존 SMS 템플릿 {deleted_count}개 삭제 완료')

        templates = [
            # 1. 입금 안내 (견적 발송)
            {
                'name': 'quotation_sent_sms',
                'type': 'sms',
                'content': '''[속기사무소 정 입금 요청]
{name} 고객님, 속기사무소 정입니다.
접수하신 파일은 작업 가능한 파일로 확인 되었습니다.

결제 금액 확인 후 계좌이체 부탁드립니다.
입금 확인 후 작업이 시작됩니다. (입금순으로 작업 진행)

<결제 안내>
- 입금액: {payment_amount}원
- 입금 계좌: 신한은행 110-597-729308 고민정
*신청자명과 입금자명이 다를 경우 고객센터로 연락 부탁드립니다.

<영수증 발행>
- 현금영수증은 신청 시 기재해주신 번호로 발행됩니다.
- 기타 요청은 고객센터로 연락 부탁드립니다. (현금영수증 번호 변경, 현금영수증 전표 발송, 세금계산서 발행)

<작업 예상 소요시간>
신청 파일 길이에 따라, 입금일로부터 초안 발송까지 1영업일 소요 예상됩니다.
* 금요일~주말 입금 건은 지연될 수 있습니다.

<청취불능표시>
아래의 경우 청취불능표시가 다수 포함될 수 있습니다.
- 음질 상태 불량, 말소리 겹침, 지나치게 작은 음량, 주변 소음

<고객센터>
- 대표번호: 010-2681-2571
- 대표메일: info@sokgijung.com
- 카톡채널: @속기사무소 정'''
            },

            # 2. 입금 확인 (결제 완료)
            {
                'name': 'payment_completed_sms',
                'type': 'sms',
                'content': '''[속기사무소 정 입금 확인]
{name} 고객님, 속기사무소 정입니다.
입금이 확인되어 곧 작업이 시작됩니다. 감사합니다.
- 입금액: {payment_amount}원'''
            },

            # 3. 초안/수정안 발송
            {
                'name': 'draft_sent_sms',
                'type': 'sms',
                'content': '''[속기사무소 정 속기록 확인 요청]
{name} 고객님, 속기사무소 정입니다.
고객님의 메일로 완성된 속기록을 발송했습니다. 확인 부탁드립니다. 감사합니다.'''
            },

            # 4. 최종안 발송
            {
                'name': 'final_sent_sms',
                'type': 'sms',
                'content': '''[속기사무소 정 최종본 발송 안내]
{name} 고객님, 속기사무소 정입니다.
고객님의 메일로 속기록 최종본을 발송했습니다. 확인 부탁드립니다. 감사합니다.'''
            }
        ]

        created_count = 0

        for template_data in templates:
            template = Template.objects.create(
                name=template_data['name'],
                type=template_data['type'],
                content=template_data['content']
            )
            created_count += 1

            # 글자 수 계산 (LMS 필요 여부 확인)
            char_count = len(template_data['content'])
            message_type = 'LMS' if char_count > 90 else 'SMS'

            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ 템플릿 생성: {template_data['name']} ({char_count}자, {message_type})"
                )
            )

        self.stdout.write(self.style.SUCCESS(f'\n✅ SMS 템플릿 생성 완료!'))
        self.stdout.write(f'- 생성: {created_count}개')
        self.stdout.write(f'- 총 SMS 템플릿: {Template.objects.filter(type="sms").count()}개')

        # 이메일 템플릿은 그대로 유지
        email_count = Template.objects.filter(type='email').count()
        self.stdout.write(f'- 총 Email 템플릿: {email_count}개 (변경 없음)')
