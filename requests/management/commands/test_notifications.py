"""
알림 시스템 테스트 관리 명령어
사용법: python manage.py test_notifications --phone 01012345678 --email test@example.com
"""
from django.core.management.base import BaseCommand, CommandError
from requests.models import Request
from notification_service.notification_service import notification_service


class Command(BaseCommand):
    help = '알림 시스템 테스트'

    def add_arguments(self, parser):
        parser.add_argument(
            '--phone',
            type=str,
            help='테스트 SMS 수신 번호 (예: 01012345678)'
        )
        parser.add_argument(
            '--email',
            type=str,
            help='테스트 이메일 주소'
        )
        parser.add_argument(
            '--request-id',
            type=int,
            help='테스트할 Request ID (실제 데이터 사용)'
        )
        parser.add_argument(
            '--status',
            type=str,
            default='payment_completed',
            help='테스트할 상태 (기본: payment_completed)'
        )

    def handle(self, *args, **options):
        phone = options.get('phone')
        email = options.get('email')
        request_id = options.get('request_id')
        status = options.get('status')

        if not phone and not email:
            raise CommandError('--phone 또는 --email 중 하나는 필수입니다.')

        self.stdout.write(self.style.SUCCESS('🚀 알림 시스템 테스트 시작'))

        # 1. 연결 테스트
        self.test_service_connection(phone, email)
        
        # 2. 템플릿 테스트
        if request_id:
            self.test_with_real_data(request_id, status, phone, email)
        else:
            self.test_with_dummy_data(status, phone, email)

    def test_service_connection(self, phone, email):
        """서비스 연결 테스트"""
        self.stdout.write('\n📡 서비스 연결 테스트')
        
        # 간단한 테스트 메시지 발송
        result = notification_service.send_test_notification(phone, email)
        
        if phone:
            if result['sms'] and result['sms']['success']:
                self.stdout.write(self.style.SUCCESS(f'✓ SMS 발송 성공: {phone}'))
            else:
                error = result['sms']['error'] if result['sms'] else 'SMS 설정 확인 필요'
                self.stdout.write(self.style.ERROR(f'✗ SMS 발송 실패: {error}'))
        
        if email:
            if result['email'] and result['email']['success']:
                self.stdout.write(self.style.SUCCESS(f'✓ 이메일 발송 성공: {email}'))
            else:
                error = result['email']['error'] if result['email'] else '이메일 설정 확인 필요'
                self.stdout.write(self.style.ERROR(f'✗ 이메일 발송 실패: {error}'))

    def test_with_real_data(self, request_id, status, phone, email):
        """실제 데이터로 템플릿 테스트"""
        self.stdout.write(f'\n📋 실제 데이터 테스트 (Request ID: {request_id})')
        
        try:
            request_obj = Request.objects.get(id=request_id)
            self.stdout.write(f'대상: {request_obj.name} ({request_obj.email})')
            
            # 임시로 테스트 연락처로 변경
            original_phone = request_obj.phone
            original_email = request_obj.email
            
            if phone:
                request_obj.phone = phone
            if email:
                request_obj.email = email
            
            # 알림 발송 테스트
            result = notification_service.send_status_notification(
                request_obj, status, 'received',
                send_sms=bool(phone), send_email=bool(email)
            )
            
            # 원래 연락처 복원
            request_obj.phone = original_phone
            request_obj.email = original_email
            
            self.print_result(result, status)
            
        except Request.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Request ID {request_id}를 찾을 수 없습니다.'))

    def test_with_dummy_data(self, status, phone, email):
        """더미 데이터로 템플릿 테스트"""
        self.stdout.write(f'\n🧪 더미 데이터 테스트 (상태: {status})')
        
        # 더미 Request 객체 생성 (저장하지 않음)
        from datetime import datetime
        dummy_request = Request(
            id=9999,
            name='홍길동',
            email=email or 'test@example.com',
            phone=phone or '010-1234-5678',
            address='서울시 강남구',
            order_id=12345,
            request_id='241221_1201',
            status='received',
            recording_date=datetime(2024, 12, 20, 14, 30, 0),
            speaker_count=2,
            estimated_price=50000,
            payment_amount=50000,
            payment_status=True,
            draft_format='hwp',
            final_option='file'
        )
        
        # 알림 발송 테스트
        result = notification_service.send_status_notification(
            dummy_request, status, 'received',
            send_sms=bool(phone), send_email=bool(email)
        )
        
        self.print_result(result, status)

    def print_result(self, result, status):
        """결과 출력"""
        self.stdout.write(f'\n📊 발송 결과 (상태: {status})')
        
        if result['sms']:
            if result['sms']['success']:
                self.stdout.write(self.style.SUCCESS('✓ SMS 발송 성공'))
            else:
                self.stdout.write(self.style.ERROR(f'✗ SMS 발송 실패: {result["sms"]["error"]}'))
        
        if result['email']:
            if result['email']['success']:
                self.stdout.write(self.style.SUCCESS('✓ 이메일 발송 성공'))
            else:
                self.stdout.write(self.style.ERROR(f'✗ 이메일 발송 실패: {result["email"]["error"]}'))
        
        if result['success']:
            self.stdout.write(self.style.SUCCESS('\n🎉 전체 알림 발송 성공!'))
        else:
            self.stdout.write(self.style.WARNING('\n⚠️  일부 알림 발송 실패'))
            if result['errors']:
                for error in result['errors']:
                    self.stdout.write(self.style.ERROR(f'  - {error}'))