from celery import shared_task
from .models import Request, Template, SendLog
from .services import MessageService

@shared_task
def send_notification(request_id, template_id):
    try:
        request = Request.objects.get(id=request_id)
        template = Template.objects.get(id=template_id)
        
        # 템플릿 변수 치환
        context_data = {
            '신청자명': request.name,
            '접수번호': f'REQ{request.id:06d}',
            '예정일': request.recording_date.strftime('%Y-%m-%d %H:%M') if request.recording_date else '미정',
            '녹음장소': request.recording_location or '미정',
        }
        
        message_content = MessageService.replace_template_variables(
            template.content,
            context_data
        )
        
        # 발송 방식에 따라 처리
        if template.type == 'sms':
            success = MessageService.send_sms(request.phone, message_content)
        else:  # email
            subject = f'[녹취 서비스] {request.name}님의 신청 안내'
            success = MessageService.send_email(request.email, subject, message_content)
        
        # 발송 로그 기록
        SendLog.objects.create(
            recipient_name=request.name,
            contact=request.phone if template.type == 'sms' else request.email,
            template=template,
            send_method=template.type,
            is_success=success
        )
        
        return success
    except Exception as e:
        print(f"알림 발송 실패: {str(e)}")
        return False 