from django.shortcuts import render
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from .models import Request, Template, SendLog, File, StatusChangeLog
from .serializers import RequestSerializer, TemplateSerializer, SendLogSerializer, FileSerializer
from .tasks import send_notification
from .utils import generate_presigned_url, validate_file_size
import boto3
from django.conf import settings
from rest_framework.views import APIView
import uuid
from rest_framework.permissions import AllowAny
from django.utils import timezone
import logging
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from django.db.models import Q, Count, Sum, Avg
from django.db.models.functions import TruncDate, TruncMonth, TruncYear
from datetime import datetime, timedelta
from decimal import Decimal
from notification_service.bulk_email_service import BulkEmailService

logger = logging.getLogger(__name__)

# Create your views here.

class RequestViewSet(viewsets.ModelViewSet):
    queryset = Request.objects.all()
    serializer_class = RequestSerializer
    parser_classes = (JSONParser, MultiPartParser, FormParser)
    permission_classes = [AllowAny]
    lookup_field = 'request_id'

    def get_queryset(self):
        """
        쿼리 최적화: 연관된 파일과 트랜스크립트를 한 번에 조회 (N+1 문제 해결)
        """
        return Request.objects.select_related('transcript_file').prefetch_related('files')

    def get_object(self):
        """
        request_id 또는 pk로 객체를 조회합니다.
        """
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}

        try:
            obj = self.queryset.get(**filter_kwargs)
        except Request.DoesNotExist:
            # request_id로 찾지 못하면 pk로 시도 (하위 호환성)
            try:
                obj = self.queryset.get(pk=self.kwargs[lookup_url_kwarg])
            except (Request.DoesNotExist, ValueError):
                from django.http import Http404
                raise Http404

        self.check_object_permissions(self.request, obj)
        return obj

    def destroy(self, request, *args, **kwargs):
        """
        요청서 삭제 시 연관된 모든 파일을 S3에서도 삭제합니다.
        """
        instance = self.get_object()
        logger.info(f'[INFO] 요청서 삭제 시작 - ID: {instance.id}')
        
        # S3 클라이언트 생성
        try:
            s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_S3_REGION_NAME
            )
            logger.info('[INFO] S3 클라이언트 생성 성공')
        except Exception as e:
            logger.error(f'[ERROR] S3 클라이언트 생성 실패: {str(e)}')
            return Response(
                {'error': f'S3 클라이언트 생성 실패: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # 연관된 모든 파일에 대해 S3에서 삭제
        files = instance.files.all()
        logger.info(f'[INFO] 삭제할 파일 수: {files.count()}')
        
        for file_instance in files:
            try:
                logger.info(f'[INFO] S3 파일 삭제 시도 - Key: {file_instance.file}')
                response = s3_client.delete_object(
                    Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                    Key=file_instance.file
                )
                logger.info(f'[INFO] S3 파일 삭제 성공 - Key: {file_instance.file}, Response: {response}')
            except Exception as e:
                logger.error(f'[ERROR] S3 파일 삭제 실패 - Key: {file_instance.file}, Error: {str(e)}')
                # S3 삭제 실패해도 계속 진행
        
        # 요청서 삭제 (CASCADE로 인해 연관된 파일들도 자동 삭제됨)
        try:
            self.perform_destroy(instance)
            logger.info(f'[INFO] 요청서 삭제 완료 - ID: {instance.id}')
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            logger.error(f'[ERROR] 요청서 삭제 실패 - ID: {instance.id}, Error: {str(e)}')
            return Response(
                {'error': f'요청서 삭제 실패: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def perform_create(self, serializer):
        request = serializer.save()
        
        # 신청 접수 알림 템플릿 조회 및 발송
        try:
            template = Template.objects.get(name='신청접수알림')
            send_notification.delay(request.id, template.id)
        except Template.DoesNotExist:
            print("신청접수알림 템플릿이 없습니다.")
    
    @action(detail=False, methods=['post'])
    def create_order_with_files(self, request):
        """
        파일별로 Request를 생성하는 새로운 API
        하나의 주문자가 여러 파일을 업로드할 때 사용
        """
        data = request.data
        
        # 프론트엔드에서 받은 견적 로깅
        estimated_price = data.get('estimated_price')
        logger.info(f'[create_order_with_files] 프론트엔드에서 받은 견적: {estimated_price}')
        
        # 기본 주문자 정보
        orderer_info = {
            'name': data.get('name'),
            'phone': data.get('phone'), 
            'email': data.get('email'),
            'address': data.get('address'),
            'draft_format': data.get('draft_format', 'hwp'),
            'final_option': data.get('final_option', 'file'),
            'agreement': data.get('agreement', True),
            'is_temporary': data.get('is_temporary', False),
            'recording_location': data.get('recording_location', '회의실'),  # 기본값
        }
        
        # Order ID 생성 (한 주문자당 하나)
        order_id = Request.generate_order_id()
        
        # 파일별 정보
        files_data = data.get('files', [])
        logger.info(f'[create_order_with_files] 파일 데이터 개수: {len(files_data)}')
        for i, file_data in enumerate(files_data):
            logger.info(f'[create_order_with_files] 파일 {i+1} 데이터:')
            logger.info(f'  - recordType: {file_data.get("recordType")}')
            logger.info(f'  - timestamps: {file_data.get("timestamps")}')
            logger.info(f'  - duration: {file_data.get("duration")}')
            logger.info(f'  - speakerNames: {file_data.get("speakerNames")}')
            logger.info(f'  - detail: {file_data.get("detail")}')
        created_requests = []
        
        for file_data in files_data:
            # 각 파일별로 Request 생성
            request_data = orderer_info.copy()
            request_data.update({
                'order_id': order_id,
                'recording_type': file_data.get('recordType', '전체'),
                'partial_range': '\n'.join(file_data.get('timestamps', [])) if file_data.get('timestamps') else '',
                'total_duration': file_data.get('duration', ''),
                'speaker_count': file_data.get('speakerCount', 1),
                'speaker_names': ','.join(file_data.get('speakerNames', [])),
                'additional_info': file_data.get('detail', ''),
                'recording_date': file_data.get('recordingDate') + ' ' + file_data.get('recordingTime', '00:00') if file_data.get('recordingDate') else None,
                'estimated_price': data.get('estimated_price'),  # 전체 견적을 각 파일에 동일하게
            })
            
            # Request 생성 (파일 생성 전까지 이메일 발송 방지)
            serializer = self.get_serializer(data=request_data, context={'skip_auto_email': True})
            if serializer.is_valid():
                request_instance = serializer.save()

                # 파일 정보 저장
                file_info = file_data.get('file_info', {})
                if file_info.get('file_key'):
                    File.objects.create(
                        request=request_instance,
                        file=file_info['file_key'],
                        original_name=file_info.get('original_name', ''),
                        file_type=file_info.get('file_type', ''),
                        file_size=file_info.get('file_size', 0)
                    )

                created_requests.append({
                    'id': request_instance.id,
                    'request_id': request_instance.request_id,
                    'order_id': request_instance.order_id
                })
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # 모든 Request와 File 생성이 완료된 후, 첫 번째 Request에서 이메일 발송
        # (이제 모든 파일 정보가 포함된 이메일이 발송됨)
        if created_requests:
            try:
                first_request = Request.objects.get(id=created_requests[0]['id'])
                first_request.send_application_completion_guide()
                logger.info(f'[create_order_with_files] 서비스 신청 완료 안내 발송 완료 - Order ID: {order_id}, 파일 수: {len(created_requests)}')
            except Exception as e:
                logger.error(f'[create_order_with_files] 이메일 발송 실패 - Order ID: {order_id}, Error: {str(e)}')
                # 이메일 발송 실패해도 Request/File 생성은 성공적으로 완료됨

        return Response({
            'success': True,
            'order_id': order_id,
            'requests': created_requests,
            'message': f'{len(created_requests)}개의 요청이 생성되었습니다.'
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def change_status(self, request, request_id=None):
        """상태 변경 API"""
        try:
            request_instance = self.get_object()
            new_status = request.data.get('status')
            reason = request.data.get('reason', '')
            skip_notification = request.data.get('skip_notification', False)  # 알림 스킵 플래그
            
            if not new_status:
                return Response({'error': '새로운 상태가 필요합니다.'}, status=status.HTTP_400_BAD_REQUEST)
            
            # 임시로 모든 상태 변경 허용 (상태 전환 규칙 비활성화)
            # if not request_instance.can_change_to(new_status):
            #     return Response({
            #         'error': f'현재 상태({request_instance.get_status_display()})에서 {new_status}로 변경할 수 없습니다.'
            #     }, status=status.HTTP_400_BAD_REQUEST)
            
            old_status = request_instance.status
            request_instance.status = new_status
            
            # 특별한 상태별 처리
            if new_status == 'impossible' and reason:
                request_instance.impossible_reason = reason
            elif new_status == 'cancelled' and reason:
                request_instance.cancel_reason = reason
            elif new_status == 'refunded' and reason:
                # 환불 금액 파싱
                if '환불금액:' in reason:
                    try:
                        amount_str = reason.split('환불금액:')[1].split('원')[0].strip().replace(',', '')
                        request_instance.refund_amount = int(amount_str)
                    except:
                        pass
            
            request_instance.save()
            
            # 상태 변경 이력 저장
            StatusChangeLog.objects.create(
                request=request_instance,
                from_status=old_status,
                to_status=new_status,
                reason=reason,
                # changed_by는 나중에 인증 시스템 구축 후 추가
            )
            
            # 알림 발송 기능 제거 (상태 변경 시 자동 발송 안함)
            notification_sent = False
            
            # 상태 변경 로그에 알림 발송 여부 업데이트
            status_log = StatusChangeLog.objects.filter(
                request=request_instance,
                to_status=new_status
            ).order_by('-changed_at').first()
            
            if status_log:
                status_log.notification_sent = notification_sent
                status_log.save()
            
            return Response({
                'success': True,
                'message': '상태가 변경되었습니다.',
                'notification_sent': notification_sent
            })
            
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def change_order_status(self, request, request_id=None):
        """Order 상태 변경 API"""
        try:
            request_instance = self.get_object()
            new_status = request.data.get('status')
            reason = request.data.get('reason', '')
            skip_notification = request.data.get('skip_notification', False)
            
            if not new_status:
                return Response({'error': '새로운 상태가 필요합니다.'}, status=status.HTTP_400_BAD_REQUEST)
            
            old_status = request_instance.order_status
            request_instance.order_status = new_status
            
            # 특별한 상태별 처리
            if new_status == 'impossible' and reason:
                request_instance.impossible_reason = reason
            elif new_status == 'cancelled' and reason:
                request_instance.cancel_reason = reason
            elif new_status == 'refunded' and reason:
                # 환불 금액 파싱
                if '환불금액:' in reason:
                    try:
                        amount_str = reason.split('환불금액:')[1].split('원')[0].strip().replace(',', '')
                        request_instance.refund_amount = int(amount_str)
                    except:
                        pass
            
            request_instance.save()
            
            # Order 상태 변경 이력 저장
            StatusChangeLog.objects.create(
                request=request_instance,
                from_status=old_status,
                to_status=new_status,
                reason=reason,
                # changed_by는 나중에 인증 시스템 구축 후 추가
            )
            
            # 알림 발송 기능 제거 (Order 상태 변경 시 자동 발송 안함)
            notification_sent = False
            
            # 상태 변경 로그에 알림 발송 여부 업데이트
            status_log = StatusChangeLog.objects.filter(
                request=request_instance,
                to_status=new_status
            ).order_by('-changed_at').first()
            
            if status_log:
                status_log.notification_sent = notification_sent
                status_log.save()
            
            return Response({
                'success': True,
                'message': 'Order 상태가 변경되었습니다.',
                'notification_sent': notification_sent
            })
            
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    @action(detail=True, methods=['post'])
    def change_payment(self, request, request_id=None):
        """결제 상태 변경 API"""
        try:
            request_instance = self.get_object()
            payment_status = request.data.get('payment_status')
            
            if payment_status is None:
                return Response({'error': '결제 상태가 필요합니다.'}, status=status.HTTP_400_BAD_REQUEST)
            
            old_payment_status = request_instance.payment_status
            request_instance.payment_status = payment_status
            request_instance.save()
            
            return Response({
                'success': True,
                'message': '결제 상태가 변경되었습니다.',
                'old_payment_status': old_payment_status,
                'new_payment_status': payment_status
            })
            
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def update_field(self, request, request_id=None):
        """관리자 필드 업데이트 API"""
        try:
            request_instance = self.get_object()
            
            # 업데이트할 필드들 확인
            allowed_fields = [
                'payment_amount', 'refund_amount', 'price_change_reason', 
                'cancel_reason', 'notes'
            ]
            
            for field_name, value in request.data.items():
                if field_name in allowed_fields:
                    setattr(request_instance, field_name, value)
            
            request_instance.save()
            
            return Response({
                'success': True,
                'message': '필드가 업데이트되었습니다.'
            })
            
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def upload_transcript(self, request, request_id=None):
        """속기록 파일 업로드 API (텍스트 파일만)"""
        try:
            request_instance = self.get_object()
            file = request.FILES.get('file')
            
            if not file:
                return Response({'error': '파일이 없습니다.'}, status=status.HTTP_400_BAD_REQUEST)
            
            # 파일 형식 검증 (텍스트 파일만)
            ALLOWED_TRANSCRIPT_EXTENSIONS = ['txt', 'hwp', 'doc', 'docx', 'pdf']
            file_extension = file.name.split('.')[-1].lower() if '.' in file.name else ''
            
            if file_extension not in ALLOWED_TRANSCRIPT_EXTENSIONS:
                return Response({
                    'error': f'텍스트 파일만 업로드 가능합니다. ({file_extension})\n허용 형식: txt, hwp, doc, docx, pdf'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # S3 클라이언트 생성
            s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_S3_REGION_NAME
            )
            
            # 기존 파일이 있다면 삭제
            if request_instance.transcript_file:
                try:
                    logger.info(f'[upload_transcript] 기존 파일 삭제 시도: {request_instance.transcript_file.file}')
                    s3_client.delete_object(
                        Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                        Key=request_instance.transcript_file.file
                    )
                    request_instance.transcript_file.delete()  # DB에서도 삭제
                    logger.info(f'[upload_transcript] 기존 파일 삭제 완료')
                except Exception as delete_error:
                    logger.error(f'[upload_transcript] 기존 파일 삭제 실패: {str(delete_error)}')
                    pass
            
            # 새 파일명 생성
            file_extension = file.name.split('.')[-1] if '.' in file.name else ''
            timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
            s3_key = f"transcripts/{request_instance.id}_transcript_{timestamp}.{file_extension}"
            
            # S3에 새 파일 업로드
            s3_client.upload_fileobj(
                file,
                settings.AWS_STORAGE_BUCKET_NAME,
                s3_key,
                ExtraArgs={'ContentType': file.content_type}
            )

            # File 모델 인스턴스 생성 (속기록 파일은 files 컬렉션에 포함하지 않음)
            from .models import File
            new_file = File.objects.create(
                request=None,  # 속기록 파일은 files 컬렉션과 분리
                file=s3_key,
                original_name=file.name,
                file_type=file.content_type,
                file_size=file.size
            )

            # Request의 transcript_file 연결
            request_instance.transcript_file = new_file
            request_instance.save()
            
            logger.info(f'[upload_transcript] 파일 업로드 완료: {file.name} -> {s3_key}')
            
            return Response({
                'success': True,
                'message': '파일이 업로드되었습니다.',
                'file_key': s3_key,
                'original_name': file.name
            })
            
        except Exception as e:
            logger.error(f'[upload_transcript] 오류: {str(e)}')
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def get_upload_url(self, request, request_id=None):
        """
        파일 업로드를 위한 Presigned URL을 생성합니다.
        """
        file_name = request.data.get('file_name')
        file_type = request.data.get('file_type')
        file_size = request.data.get('file_size')
        customer_name = request.data.get('customer_name')
        customer_email = request.data.get('customer_email')
        
        if not all([file_name, file_type, file_size, customer_name, customer_email]):
            return Response(
                {'error': '파일 정보가 부족합니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # 이메일에서 @ 앞부분만 추출
        email_id = customer_email.split('@')[0] if customer_email else 'unknown'
        # S3 key: 고객명+이메일아이디/원본파일명
        s3_key = f"{customer_name}_{email_id}/{file_name}"
        print('s3_key:', s3_key, flush=True)
        
        # 파일 크기 검증
        if not validate_file_size(int(file_size)):
            return Response(
                {'error': '파일 크기가 제한을 초과합니다. (최대 500MB)'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Presigned URL 생성
        try:
            url_info = generate_presigned_url(file_name, file_type, s3_key=s3_key)
            print('presigned_post url_info:', url_info)
            return Response(url_info)
        except Exception as e:
            return Response(
                {'error': f'URL 생성 실패: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def upload_file(self, request, request_id=None):
        request_obj = self.get_object()
        # S3 presigned 업로드 방식: 실제 파일은 이미 S3에 업로드됨
        file_name = request.data.get('file_name')
        file_type = request.data.get('file_type')
        file_size = request.data.get('file_size')
        s3_key = request.data.get('file_key') or request.data.get('s3_key')
        
        if not all([file_name, file_type, file_size, s3_key]):
            return Response(
                {'error': 'file_name, file_type, file_size, s3_key는 필수입니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            # FileField에 S3 key를 직접 할당
            file_instance = File.objects.create(
                request=request_obj,
                file=s3_key,  # S3 key를 직접 저장
                original_name=file_name,
                file_type=file_type,
                file_size=file_size
            )
            serializer = FileSerializer(file_instance, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f'파일 정보 저장 실패: {str(e)}')
            return Response(
                {'error': f'파일 정보 저장 실패: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['delete'])
    def delete_file(self, request, request_id=None):
        file_key = request.data.get('file_key')
        print('[DEBUG] delete_file API 진입, file_key:', file_key, flush=True)
        if not file_key:
            return Response(
                {'error': '파일 키가 필요합니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # DB에서 파일 정보 찾기 (선택적)
        file_instance = None
        try:
            file_instance = File.objects.get(request_id=pk, file=file_key)
            print('[DEBUG] DB에서 찾은 file_instance.file:', file_instance.file, flush=True)
        except File.DoesNotExist:
            print('[DEBUG] DB에서 파일을 찾을 수 없음, S3에서만 삭제 시도', flush=True)
        
        # S3에서 파일 삭제
        try:
            s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_S3_REGION_NAME
            )
            print('[DEBUG] S3 삭제 시도 key:', file_key, flush=True)
            s3_client.delete_object(
                Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                Key=file_key
            )
        except Exception as e:
            print('[DEBUG] S3 파일 삭제 실패:', str(e), flush=True)
            return Response(
                {'error': f'S3 파일 삭제 실패: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
        # DB에 파일 정보가 있었다면 삭제
        if file_instance:
            file_instance.delete()
            print('[DEBUG] DB 파일 정보 삭제 완료', flush=True)
        
        print('[DEBUG] 파일 삭제 완료', flush=True)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get'])
    def files(self, request, request_id=None):
        """
        해당 request에 업로드된 파일 리스트를 반환합니다.
        """
        request_obj = self.get_object()
        files = request_obj.files.all()
        serializer = FileSerializer(files, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def submit(self, request, request_id=None):
        """
        서비스 신청 완료 시 호출. is_temporary를 False로 변경.
        """
        request_obj = self.get_object()
        request_obj.is_temporary = False
        request_obj.save()
        serializer = self.get_serializer(request_obj)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        # is_temporary 값이 없으면 True로 강제
        if 'is_temporary' not in data:
            data['is_temporary'] = True
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        data = request.data.copy()
        # is_temporary 값이 명시적으로 False로 오면 정식 신청서로 전환
        if 'is_temporary' in data and (data['is_temporary'] == False or data['is_temporary'] == 'false' or data['is_temporary'] == 0 or data['is_temporary'] == '0'):
            data['is_temporary'] = False
        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

class TemplateViewSet(viewsets.ModelViewSet):
    queryset = Template.objects.all()
    serializer_class = TemplateSerializer
    permission_classes = [permissions.IsAuthenticated]

class SendLogViewSet(viewsets.ModelViewSet):
    queryset = SendLog.objects.all()
    serializer_class = SendLogSerializer
    permission_classes = [permissions.IsAuthenticated]

class S3PresignedURLView(APIView):
    permission_classes = [AllowAny]

    # 허용 확장자 및 MIME 타입 목록 (영상/음성 파일만 - 주문서용)
    ALLOWED_EXTENSIONS = {
        # 음성 파일
        'mp3', 'wav', 'm4a', 'cda', 'mod', 'ogg', 'wma', 'flac', 'asf',
        # 영상 파일
        'avi', 'mp4', 'wmv', 'm2v', 'mpeg', 'dpg', 'mts', 'webm', 'divx', 'amv',
        # 추가 영상 형식
        'm4v', 'mov'
    }
    ALLOWED_MIME_TYPES = {
        # 음성 MIME
        'audio/mpeg', 'audio/wav', 'audio/x-wav', 'audio/mp4', 'audio/x-m4a', 
        'audio/ogg', 'audio/x-ms-wma', 'audio/flac', 'audio/x-flac',
        # 영상 MIME
        'video/mp4', 'video/x-ms-asf', 'video/x-m4v', 'video/quicktime',
        'video/x-ms-wmv', 'video/x-msvideo', 'video/mpeg', 'video/webm',
        'video/x-matroska', 'application/octet-stream'
    }
    MAX_FILE_SIZE = 3 * 1024 * 1024 * 1024  # 3GB

    def post(self, request):
        try:
            file_name = request.data.get('file_name')
            file_type = request.data.get('file_type')
            file_size = request.data.get('file_size')

            if not file_name or not file_type or not file_size:
                return Response(
                    {'error': 'file_name, file_type, file_size는 필수입니다.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 확장자 체크 (영상/음성 파일만)
            ext = file_name.split('.')[-1].lower()
            if ext not in self.ALLOWED_EXTENSIONS:
                return Response(
                    {'error': f'영상/음성 파일만 업로드 가능합니다. ({ext})\n허용 형식: mp3, wav, m4a, avi, mp4, wmv 등'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # MIME 타입 체크 (영상/음성만)
            if file_type not in self.ALLOWED_MIME_TYPES:
                return Response(
                    {'error': f'영상/음성 파일만 업로드 가능합니다. (파일 타입: {file_type})'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 파일 크기 체크
            try:
                file_size_int = int(file_size)
            except Exception:
                return Response({'error': 'file_size는 숫자여야 합니다.'}, status=status.HTTP_400_BAD_REQUEST)
            if file_size_int > self.MAX_FILE_SIZE:
                return Response(
                    {'error': '파일 크기가 3GB를 초과합니다.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # S3 클라이언트 생성 (Signature V4 강제)
            from botocore.config import Config
            s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_S3_REGION_NAME,
                config=Config(signature_version='s3v4')
            )

            unique_file_name = f"{uuid.uuid4()}_{file_name}"

            # S3 presigned POST 정책
            conditions = [
                ["content-length-range", 1, self.MAX_FILE_SIZE],
                {"Content-Type": file_type},
                ["starts-with", "$key", ""],
            ]
            fields = {
                "Content-Type": file_type,
                "key": unique_file_name,
            }

            presigned_post = s3_client.generate_presigned_post(
                Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                Key=unique_file_name,
                Fields=fields,
                Conditions=conditions,
                ExpiresIn=3600
            )

            # 리전별 엔드포인트로 URL 수정
            presigned_post['url'] = presigned_post['url'].replace(
                'https://go-stenographe-web.s3.amazonaws.com/',
                f'https://go-stenographe-web.s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/'
            )

            return Response({
                'presigned_post': presigned_post,
                'file_name': unique_file_name
            })

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class S3DeleteView(APIView):
    def delete(self, request):
        try:
            file_key = request.data.get('file_key')
            if not file_key:
                return Response({'error': 'file_key is required'}, status=status.HTTP_400_BAD_REQUEST)

            logger.debug(f'[DEBUG] S3 파일 삭제 시도: {file_key}')
            
            s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_S3_REGION_NAME
            )
            
            try:
                s3_client.delete_object(
                    Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                    Key=file_key
                )
                logger.debug(f'[DEBUG] S3 파일 삭제 성공: {file_key}')
                return Response({'message': 'File deleted successfully'}, status=status.HTTP_200_OK)
            except Exception as e:
                logger.error(f'[ERROR] S3 파일 삭제 실패: {str(e)}')
                return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except Exception as e:
            logger.error(f'[ERROR] S3 파일 삭제 중 예외 발생: {str(e)}')
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def download_file(self, request):
        """S3 파일 다운로드 API"""
        file_key = request.query_params.get('file_key')
        
        logger.info(f'[download_file] 다운로드 요청 - file_key: {file_key}')
        
        if not file_key:
            logger.error('[download_file] file_key 파라미터가 없음')
            return Response({'error': 'file_key 파라미터가 필요합니다.'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # 파일 정보 확인
            from .models import File
            try:
                file_obj = File.objects.get(file=file_key)
                logger.info(f'[download_file] 파일 정보 - 원본명: {file_obj.original_name}, 타입: {file_obj.file_type}, 크기: {file_obj.file_size}')
            except File.DoesNotExist:
                logger.warning(f'[download_file] 데이터베이스에서 파일을 찾을 수 없음: {file_key}')
            
            # S3 파일 존재 여부 확인
            s3_client = boto3.client('s3')
            try:
                s3_response = s3_client.head_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=file_key)
                logger.info(f'[download_file] S3 파일 확인 - 크기: {s3_response.get("ContentLength")} bytes, 타입: {s3_response.get("ContentType")}')
            except Exception as s3_error:
                logger.error(f'[download_file] S3에서 파일을 찾을 수 없음: {str(s3_error)}')
                return Response({'error': f'파일을 찾을 수 없습니다: {file_key}'}, status=status.HTTP_404_NOT_FOUND)
            
            # S3에서 파일 다운로드 URL 생성 (1시간 유효)
            download_url = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': settings.AWS_STORAGE_BUCKET_NAME, 'Key': file_key},
                ExpiresIn=3600  # 1시간
            )
            
            logger.info(f'[download_file] Presigned URL 생성 완료: {download_url[:100]}...')
            
            # 리다이렉트로 다운로드
            from django.http import HttpResponseRedirect
            return HttpResponseRedirect(download_url)
            
        except Exception as e:
            logger.error(f'[download_file] 파일 다운로드 실패: {str(e)}')
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def download_file_view(request):
    """간단한 파일 다운로드 뷰"""
    file_key = request.GET.get('file_key')
    
    if not file_key:
        from django.http import JsonResponse
        return JsonResponse({'error': 'file_key 파라미터가 필요합니다.'}, status=400)
    
    try:
        # S3에서 presigned URL 생성
        s3_client = boto3.client('s3')
        download_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': settings.AWS_STORAGE_BUCKET_NAME, 'Key': file_key},
            ExpiresIn=3600  # 1시간
        )
        
        # 리다이렉트로 다운로드
        from django.http import HttpResponseRedirect
        return HttpResponseRedirect(download_url)
        
    except Exception as e:
        from django.http import JsonResponse
        return JsonResponse({'error': str(e)}, status=500)

@method_decorator(staff_member_required, name='dispatch')
class ExcelDatabaseView(TemplateView):
    template_name = 'admin/excel_database.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 실제 Request 모델 데이터 사용
        from .models import Request
        from django.contrib.admin.views.main import ChangeList
        from django.contrib import admin
        
        # Django admin의 ChangeList를 활용하여 데이터 가져오기
        request_queryset = Request.objects.all().order_by('-created_at')
        
        # ChangeList 객체 생성 (admin 페이지와 동일한 구조)
        class RequestChangeList:
            def __init__(self, queryset):
                self.result_list = queryset
                
        cl = RequestChangeList(request_queryset)
        
        context['cl'] = cl
        context['title'] = '엑셀 데이터베이스'
        context['opts'] = {'app_label': 'requests', 'model_name': 'request'}
        return context

@staff_member_required
def statistics_dashboard_view(request):
    """통계 대시보드 뷰"""
    # 기본 통계 데이터
    total_requests = Request.objects.count()
    total_files = File.objects.count()
    total_revenue = Request.objects.filter(
        payment_status=True
    ).aggregate(
        total=Sum('payment_amount')
    )['total'] or 0
    
    # 일별 접수량 (최근 30일) - 파일 JOIN 제거
    thirty_days_ago = timezone.now() - timedelta(days=30)
    daily_stats = Request.objects.filter(
        created_at__gte=thirty_days_ago
    ).extra(
        select={'date': "DATE(requests_request.created_at)"}
    ).values('date').annotate(
        count=Count('id'),
        revenue=Sum('payment_amount')
    ).order_by('date')
    
    # 월별 통계 (최근 12개월)
    twelve_months_ago = timezone.now() - timedelta(days=365)
    monthly_stats = Request.objects.filter(
        created_at__gte=twelve_months_ago
    ).extra(
        select={
            'month': "strftime('%%Y-%%m-01', requests_request.created_at)"
        }
    ).values('month').annotate(
        count=Count('id'),
        revenue=Sum('payment_amount')
    ).order_by('month')
    
    # 연도별 통계
    yearly_stats = Request.objects.extra(
        select={
            'year': "strftime('%%Y-01-01', requests_request.created_at)"
        }
    ).values('year').annotate(
        count=Count('id'),
        revenue=Sum('payment_amount')
    ).order_by('year')
    
    # 상태별 통계
    status_stats = Request.objects.values('status').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # 최종본 옵션 선호도
    final_option_stats = Request.objects.values('final_option').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # 취소 관련 통계
    cancelled_stats = Request.objects.filter(
        status__in=['cancelled', 'refunded', 'impossible']
    ).values('status').annotate(
        count=Count('id')
    )
    
    # 평균 주문금액 계산
    average_order_amount = 0
    if total_requests > 0 and total_revenue:
        average_order_amount = total_revenue / total_requests
    
    context = {
        'total_requests': total_requests,
        'total_files': total_files,
        'total_revenue': total_revenue,
        'average_order_amount': average_order_amount,
        'daily_stats': list(daily_stats),
        'monthly_stats': list(monthly_stats),
        'yearly_stats': list(yearly_stats),
        'status_stats': list(status_stats),
        'final_option_stats': list(final_option_stats),
        'cancelled_stats': list(cancelled_stats),
    }
    
    return render(request, 'admin/statistics_dashboard.html', context)

@staff_member_required  
def statistics_api_view(request):
    """AJAX용 통계 데이터 API"""
    period = request.GET.get('period', 'total')
    
    # 기본 통계 데이터
    total_requests = Request.objects.count()
    total_files = File.objects.count()
    total_revenue = Request.objects.filter(
        payment_status=True
    ).aggregate(
        total=Sum('payment_amount')
    )['total'] or 0
    
    # 평균 주문금액 계산
    average_order_amount = 0
    if total_requests > 0 and total_revenue:
        average_order_amount = total_revenue / total_requests
    
    # 기간별 트렌드 데이터
    trend_data = []
    revenue_data = []
    labels = []
    
    if period == '1일':
        # 24시간별 데이터
        now = timezone.now()
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        for hour in range(24):
            hour_start = start_of_day + timedelta(hours=hour)
            hour_end = hour_start + timedelta(hours=1)
            
            requests_count = Request.objects.filter(
                created_at__gte=hour_start,
                created_at__lt=hour_end
            ).count()
            
            revenue_sum = Request.objects.filter(
                created_at__gte=hour_start,
                created_at__lt=hour_end,
                payment_status=True
            ).aggregate(total=Sum('payment_amount'))['total'] or 0
            
            trend_data.append(requests_count)
            revenue_data.append(float(revenue_sum))
            labels.append(f"{hour}시")
            
    elif period == '30일':
        # 30일간 일별 데이터
        now = timezone.now()
        
        for i in range(29, -1, -1):
            date = now.date() - timedelta(days=i)
            day_start = timezone.make_aware(datetime.combine(date, datetime.min.time()))
            day_end = day_start + timedelta(days=1)
            
            requests_count = Request.objects.filter(
                created_at__gte=day_start,
                created_at__lt=day_end
            ).count()
            
            revenue_sum = Request.objects.filter(
                created_at__gte=day_start,
                created_at__lt=day_end,
                payment_status=True
            ).aggregate(total=Sum('payment_amount'))['total'] or 0
            
            trend_data.append(requests_count)
            revenue_data.append(float(revenue_sum))
            labels.append(f"{date.month}/{date.day}")
            
    elif period == '12개월':
        # 12개월간 월별 데이터
        now = timezone.now()
        
        for i in range(11, -1, -1):
            month_date = now.replace(day=1) - timedelta(days=32*i)
            month_start = month_date.replace(day=1)
            if month_start.month == 12:
                month_end = month_start.replace(year=month_start.year + 1, month=1)
            else:
                month_end = month_start.replace(month=month_start.month + 1)
            
            requests_count = Request.objects.filter(
                created_at__gte=month_start,
                created_at__lt=month_end
            ).count()
            
            revenue_sum = Request.objects.filter(
                created_at__gte=month_start,
                created_at__lt=month_end,
                payment_status=True
            ).aggregate(total=Sum('payment_amount'))['total'] or 0
            
            trend_data.append(requests_count)
            revenue_data.append(float(revenue_sum))
            labels.append(f"{month_start.month}월")
            
    elif period == '연도별':
        # 최근 5년간 연도별 데이터
        current_year = timezone.now().year
        
        for i in range(4, -1, -1):
            year = current_year - i
            year_start = timezone.make_aware(datetime(year, 1, 1))
            year_end = timezone.make_aware(datetime(year + 1, 1, 1))
            
            requests_count = Request.objects.filter(
                created_at__gte=year_start,
                created_at__lt=year_end
            ).count()
            
            revenue_sum = Request.objects.filter(
                created_at__gte=year_start,
                created_at__lt=year_end,
                payment_status=True
            ).aggregate(total=Sum('payment_amount'))['total'] or 0
            
            trend_data.append(requests_count)
            revenue_data.append(float(revenue_sum))
            labels.append(f"{year}년")
    
    # 상태별 통계
    status_stats = Request.objects.values('status').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # 최종본 옵션 선호도
    final_option_stats = Request.objects.values('final_option').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # 취소 관련 통계
    cancelled_stats = Request.objects.filter(
        status__in=['cancelled', 'refunded', 'impossible']
    ).values('status').annotate(
        count=Count('id')
    )
    
    data = {
        'total_requests': total_requests,
        'total_files': total_files,
        'total_revenue': float(total_revenue) if total_revenue else 0,
        'average_order_amount': float(average_order_amount),
        'status_stats': list(status_stats),
        'final_option_stats': list(final_option_stats),
        'cancelled_stats': list(cancelled_stats),
        'trend_data': trend_data,
        'revenue_data': revenue_data,
        'labels': labels,
        'last_updated': timezone.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    return JsonResponse(data)

@api_view(['POST'])
def validate_quotation_orders(request):
    """견적 발송 전 주문 검증"""
    try:
        order_ids = request.data.get('order_ids', [])

        if not order_ids:
            return Response({'error': '선택된 주문이 없습니다.'}, status=status.HTTP_400_BAD_REQUEST)

        validation_results = []

        for order_id in order_ids:
            request_obj = Request.objects.filter(order_id=order_id, is_temporary=False).first()

            result = {
                'order_id': order_id,
                'valid': True,
                'errors': [],
                'customer_name': '',
                'email': '',
                'payment_amount': None
            }

            if not request_obj:
                result['valid'] = False
                result['errors'].append('주문을 찾을 수 없습니다')
                validation_results.append(result)
                continue

            # 기본 정보 설정
            result['customer_name'] = request_obj.name
            result['email'] = request_obj.email
            result['payment_amount'] = str(request_obj.payment_amount) if request_obj.payment_amount else None

            # 검증 조건
            if request_obj.order_status != 'received':
                result['valid'] = False
                result['errors'].append(f'상태가 접수됨이 아닙니다 (현재: {request_obj.get_order_status_display()})')

            if not request_obj.payment_amount:
                result['valid'] = False
                result['errors'].append('결제 금액이 입력되지 않았습니다')

            if not request_obj.email:
                result['valid'] = False
                result['errors'].append('이메일 주소가 없습니다')

            validation_results.append(result)

        # 전체 검증 결과
        all_valid = all(r['valid'] for r in validation_results)

        return Response({
            'all_valid': all_valid,
            'results': validation_results
        })

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def send_quotation_guide(request):
    """견적 및 입금 안내 발송"""
    try:
        order_ids = request.data.get('order_ids', [])
        
        if not order_ids:
            return Response({'error': '선택된 주문이 없습니다.'}, status=status.HTTP_400_BAD_REQUEST)
        
        success_count = 0
        error_messages = []
        
        for order_id in order_ids:
            # Order ID에 해당하는 첫 번째 Request 찾기 (주문 대표)
            request_obj = Request.objects.filter(order_id=order_id, is_temporary=False).first()
            
            if not request_obj:
                error_messages.append(f'Order ID {order_id}: 주문을 찾을 수 없습니다.')
                continue
                
            # 발송 조건 검증
            if request_obj.order_status != 'received':
                error_messages.append(f'Order ID {order_id}: 상태가 접수됨이 아닙니다. (현재: {request_obj.get_order_status_display()})')
                continue

            if not request_obj.payment_amount:
                error_messages.append(f'Order ID {order_id}: 결제 금액이 입력되지 않았습니다.')
                continue

            # Order ID로 그룹화된 모든 Request 찾기
            try:
                same_order_requests = Request.objects.filter(order_id=order_id, is_temporary=False)

                # 이메일 발송 (템플릿 사용)
                bulk_service = BulkEmailService()
                result = bulk_service.send_quotation_and_deposit_guide(
                    requests=list(same_order_requests),
                    email_subject='견적 및 입금 안내'
                )
                
                if result['success_count'] > 0:
                    success_count += 1
                    print(f'[SEND EMAIL] 견적 및 입금 안내 발송 성공 - Order ID: {order_id}, Email: {request_obj.email}, Amount: {request_obj.payment_amount}')

                    # SendLog에 발송 이력 저장
                    from requests.models import SendLog
                    SendLog.objects.create(
                        request=request_obj,
                        email_type='quotation_guide',
                        order_id=order_id,
                        payment_amount=request_obj.payment_amount,
                        recipient_email=request_obj.email,
                        success=True
                    )
                else:
                    error_messages.append(f'Order ID {order_id}: 이메일 발송 실패')
            except Exception as e:
                error_messages.append(f'Order ID {order_id}: 이메일 발송 실패 - {str(e)}')
        
        return Response({
            'success': True,
            'message': f'{success_count}건의 견적 및 입금 안내를 발송했습니다.',
            'success_count': success_count,
            'errors': error_messages
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def validate_payment_completion_orders(request):
    """결제 완료 안내 발송 전 주문 검증"""
    try:
        order_ids = request.data.get('order_ids', [])

        if not order_ids:
            return Response({'error': '선택된 주문이 없습니다.'}, status=status.HTTP_400_BAD_REQUEST)

        validation_results = []

        for order_id in order_ids:
            request_obj = Request.objects.filter(order_id=order_id, is_temporary=False).first()

            result = {
                'order_id': order_id,
                'valid': True,
                'errors': [],
                'customer_name': '',
                'email': '',
                'payment_amount': None
            }

            if not request_obj:
                result['valid'] = False
                result['errors'].append('주문을 찾을 수 없습니다')
                validation_results.append(result)
                continue

            # 기본 정보 설정
            result['customer_name'] = request_obj.name
            result['email'] = request_obj.email
            result['payment_amount'] = str(request_obj.payment_amount) if request_obj.payment_amount else None

            # 검증 조건
            if request_obj.order_status != 'received':
                result['valid'] = False
                result['errors'].append(f'상태가 접수됨이 아닙니다 (현재: {request_obj.get_order_status_display()})')

            if not request_obj.payment_amount:
                result['valid'] = False
                result['errors'].append('결제 금액이 입력되지 않았습니다')

            if not request_obj.email:
                result['valid'] = False
                result['errors'].append('이메일 주소가 없습니다')

            validation_results.append(result)

        # 전체 검증 결과
        all_valid = all(r['valid'] for r in validation_results)

        return Response({
            'all_valid': all_valid,
            'results': validation_results
        })

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def send_payment_completion_guide(request):
    """결제 완료 안내 발송"""
    try:
        order_ids = request.data.get('order_ids', [])
        
        if not order_ids:
            return Response({'error': '선택된 주문이 없습니다.'}, status=status.HTTP_400_BAD_REQUEST)
        
        success_count = 0
        error_messages = []
        
        for order_id in order_ids:
            request_obj = Request.objects.filter(order_id=order_id, is_temporary=False).first()
            
            if not request_obj:
                error_messages.append(f'Order ID {order_id}: 주문을 찾을 수 없습니다.')
                continue
                
            # 발송 조건 검증
            if request_obj.order_status != 'received':
                error_messages.append(f'Order ID {order_id}: 상태가 접수됨이 아닙니다. (현재: {request_obj.get_order_status_display()})')
                continue

            if not request_obj.payment_amount:
                error_messages.append(f'Order ID {order_id}: 결제 금액이 입력되지 않았습니다.')
                continue

            # Order ID로 그룹화된 모든 Request 찾기
            try:
                same_order_requests = Request.objects.filter(order_id=order_id, is_temporary=False)

                # 이메일 발송 (템플릿 사용)
                bulk_service = BulkEmailService()
                result = bulk_service.send_payment_completion_guide(
                    requests=list(same_order_requests),
                    email_subject='결제 완료 안내'
                )
                
                if result['success_count'] > 0:
                    success_count += 1
                    print(f'[SEND EMAIL] 결제 완료 안내 발송 성공 - Order ID: {order_id}, Email: {request_obj.email}')

                    # SendLog에 발송 이력 저장
                    from requests.models import SendLog
                    SendLog.objects.create(
                        request=request_obj,
                        email_type='payment_completion_guide',
                        order_id=order_id,
                        payment_amount=request_obj.payment_amount,
                        recipient_email=request_obj.email,
                        success=True
                    )
                else:
                    error_messages.append(f'Order ID {order_id}: 이메일 발송 실패')
            except Exception as e:
                error_messages.append(f'Order ID {order_id}: 이메일 발송 실패 - {str(e)}')
        
        return Response({
            'success': True,
            'message': f'{success_count}건의 결제 완료 안내를 발송했습니다.',
            'success_count': success_count,
            'errors': error_messages
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def validate_draft_guide(request):
    """속기록 초안/수정안 발송 전 검증"""
    try:
        request_ids = request.data.get('request_ids', [])

        if not request_ids:
            return Response({'error': '선택된 요청이 없습니다.'}, status=status.HTTP_400_BAD_REQUEST)

        results = []

        for request_id in request_ids:
            request_obj = Request.objects.filter(request_id=request_id, is_temporary=False).first()

            result = {
                'request_id': request_id,
                'valid': True,
                'errors': []
            }

            if not request_obj:
                result['valid'] = False
                result['errors'].append('요청을 찾을 수 없습니다.')
                result['customer_name'] = None
                result['email'] = None
                result['transcript_file'] = None
            else:
                result['customer_name'] = request_obj.name
                result['email'] = request_obj.email
                result['transcript_file'] = request_obj.transcript_file.original_name if request_obj.transcript_file else None
                result['status'] = request_obj.status
                result['status_display'] = request_obj.get_status_display()

                # 발송 조건 검증
                if request_obj.status != 'in_progress':
                    result['valid'] = False
                    result['errors'].append(f'상태가 작업중이 아닙니다. (현재: {request_obj.get_status_display()})')

                if not request_obj.transcript_file:
                    result['valid'] = False
                    result['errors'].append('속기록 파일이 업로드되지 않았습니다.')

                if not request_obj.email:
                    result['valid'] = False
                    result['errors'].append('이메일 주소가 없습니다.')

            results.append(result)

        return Response({
            'results': results
        })

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def validate_final_draft_guide(request):
    """속기록 최종안 발송 전 검증"""
    try:
        request_ids = request.data.get('request_ids', [])

        if not request_ids:
            return Response({'error': '선택된 요청이 없습니다.'}, status=status.HTTP_400_BAD_REQUEST)

        results = []

        for request_id in request_ids:
            request_obj = Request.objects.filter(request_id=request_id, is_temporary=False).first()

            result = {
                'request_id': request_id,
                'valid': True,
                'errors': []
            }

            if not request_obj:
                result['valid'] = False
                result['errors'].append('요청을 찾을 수 없습니다.')
                result['customer_name'] = None
                result['email'] = None
                result['transcript_file'] = None
            else:
                result['customer_name'] = request_obj.name
                result['email'] = request_obj.email
                result['transcript_file'] = request_obj.transcript_file.original_name if request_obj.transcript_file else None
                result['status'] = request_obj.status
                result['status_display'] = request_obj.get_status_display()

                # 발송 조건 검증
                if request_obj.status != 'work_completed':
                    result['valid'] = False
                    result['errors'].append(f'상태가 작업완료가 아닙니다. (현재: {request_obj.get_status_display()})')

                if not request_obj.transcript_file:
                    result['valid'] = False
                    result['errors'].append('속기록 파일이 업로드되지 않았습니다.')

                if not request_obj.email:
                    result['valid'] = False
                    result['errors'].append('이메일 주소가 없습니다.')

            results.append(result)

        return Response({
            'results': results
        })

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def send_draft_guide(request):
    """속기록 초안/수정안 요청 안내 발송"""
    try:
        request_ids = request.data.get('request_ids', [])
        
        if not request_ids:
            return Response({'error': '선택된 요청이 없습니다.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # 유효한 요청들 필터링
        valid_requests = []
        error_messages = []
        
        for request_id in request_ids:
            request_obj = Request.objects.filter(request_id=request_id, is_temporary=False).first()
            
            if not request_obj:
                error_messages.append(f'Request ID {request_id}: 요청을 찾을 수 없습니다.')
                continue
                
            # 발송 조건 검증
            if request_obj.status != 'in_progress':
                error_messages.append(f'Request ID {request_id}: 상태가 작업중이 아닙니다. (현재: {request_obj.get_status_display()})')
                continue
                
            if not request_obj.transcript_file:
                error_messages.append(f'Request ID {request_id}: 속기록 파일이 업로드되지 않았습니다.')
                continue
            
            valid_requests.append(request_obj)

        if not valid_requests:
            return Response({
                'error': '발송 가능한 요청이 없습니다.',
                'errors': error_messages
            }, status=status.HTTP_400_BAD_REQUEST)

        # 대량 이메일 발송 (같은 이메일 주소끼리 파일 묶어서 발송)
        try:
            bulk_service = BulkEmailService()

            # 템플릿 기반 발송
            result = bulk_service.send_sending_drafts_guide(
                requests=valid_requests,
                email_subject='속기록 초안/수정안 발송'
            )
            
            success_count = result['success_count']
            if result['failed_emails']:
                for failed in result['failed_emails']:
                    error_messages.append(f"이메일 {failed['email']}: {failed['error']}")

            # 발송 성공한 Request에 대해 SendLog 저장
            for request_obj in valid_requests:
                try:
                    SendLog.objects.create(
                        request=request_obj,
                        email_type='draft_guide',
                        sent_request_id=request_obj.request_id,
                        recipient_email=request_obj.email,
                        success=True
                    )
                except Exception as log_error:
                    logger.error(f'[send_draft_guide] SendLog 저장 실패 - Request ID: {request_obj.request_id}, Error: {str(log_error)}')

        except Exception as e:
            return Response({'error': f'이메일 발송 중 오류: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            'success': True,
            'message': f'{success_count}건의 속기록 초안/수정안을 발송했습니다.',
            'success_count': success_count,
            'errors': error_messages
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def send_final_draft_guide(request):
    """속기록 최종안 안내 발송"""
    try:
        request_ids = request.data.get('request_ids', [])
        
        if not request_ids:
            return Response({'error': '선택된 요청이 없습니다.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # 유효한 요청들 필터링
        valid_requests = []
        error_messages = []
        
        for request_id in request_ids:
            request_obj = Request.objects.filter(request_id=request_id, is_temporary=False).first()
            
            if not request_obj:
                error_messages.append(f'Request ID {request_id}: 요청을 찾을 수 없습니다.')
                continue
                
            # 발송 조건 검증
            if request_obj.status != 'work_completed':
                error_messages.append(f'Request ID {request_id}: 상태가 작업완료가 아닙니다. (현재: {request_obj.get_status_display()})')
                continue
                
            if not request_obj.transcript_file:
                error_messages.append(f'Request ID {request_id}: 속기록 파일이 업로드되지 않았습니다.')
                continue
            
            valid_requests.append(request_obj)

        if not valid_requests:
            return Response({
                'error': '발송 가능한 요청이 없습니다.',
                'errors': error_messages
            }, status=status.HTTP_400_BAD_REQUEST)

        # 대량 이메일 발송 (같은 이메일 주소끼리 파일 묶어서 발송)
        try:
            bulk_service = BulkEmailService()

            # 템플릿 기반 발송
            result = bulk_service.send_final_draft_guide(
                requests=valid_requests,
                email_subject='속기록 최종안 발송'
            )
            
            success_count = result['success_count']
            if result['failed_emails']:
                for failed in result['failed_emails']:
                    error_messages.append(f"이메일 {failed['email']}: {failed['error']}")

            # 발송 성공한 Request에 대해 SendLog 저장
            for request_obj in valid_requests:
                try:
                    SendLog.objects.create(
                        request=request_obj,
                        email_type='final_draft_guide',
                        sent_request_id=request_obj.request_id,
                        recipient_email=request_obj.email,
                        success=True
                    )
                except Exception as log_error:
                    logger.error(f'[send_final_draft_guide] SendLog 저장 실패 - Request ID: {request_obj.request_id}, Error: {str(log_error)}')

        except Exception as e:
            return Response({'error': f'이메일 발송 중 오류: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            'success': True,
            'message': f'{success_count}건의 속기록 최종안을 발송했습니다.',
            'success_count': success_count,
            'errors': error_messages
        })

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def send_application_completion_guide(request):
    """서비스 신청 완료 안내 자동 발송"""
    try:
        request_id = request.data.get('request_id')

        if not request_id:
            return Response({'error': 'Request ID가 필요합니다.'}, status=status.HTTP_400_BAD_REQUEST)

        request_obj = Request.objects.filter(request_id=request_id).first()

        if not request_obj:
            return Response({'error': '요청을 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            # TODO: 실제 이메일 발송 로직 구현
            print(f'[SEND EMAIL] 서비스 신청 완료 안내 발송 - Request ID: {request_id}, Email: {request_obj.email}')

            return Response({
                'success': True,
                'message': '서비스 신청 완료 안내를 발송했습니다.'
            })
        except Exception as e:
            return Response({'error': f'이메일 발송 실패 - {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def check_send_history(request):
    """
    발송 이력 확인 API
    - 프로세스 1 (Order ID 기반): 견적/결제 완료 안내 - payment_amount 포함
    - 프로세스 2 (Request ID 기반): 초안/최종안 - payment_amount 불필요
    """
    try:
        email_type = request.data.get('email_type')

        if not email_type:
            return Response({'error': '이메일 종류가 필요합니다.'}, status=status.HTTP_400_BAD_REQUEST)

        duplicate_history = []

        # 프로세스 1: Order ID 기반 (견적/결제)
        if email_type in ['quotation_guide', 'payment_completion_guide']:
            order_ids = request.data.get('order_ids', [])

            if not order_ids:
                return Response({'error': '선택된 주문이 없습니다.'}, status=status.HTTP_400_BAD_REQUEST)

            for order_id in order_ids:
                # 해당 Order ID의 현재 Request 정보 가져오기
                request_obj = Request.objects.filter(order_id=order_id, is_temporary=False).first()

                if not request_obj:
                    continue

                # 현재 결제 금액
                current_payment_amount = request_obj.payment_amount

                if not current_payment_amount:
                    continue

                # 같은 Order ID + 같은 이메일 종류 + 같은 금액의 이전 발송 이력 찾기
                previous_logs = SendLog.objects.filter(
                    order_id=order_id,
                    email_type=email_type,
                    payment_amount=current_payment_amount,
                    success=True
                ).order_by('-created_at')

                if previous_logs.exists():
                    latest_log = previous_logs.first()
                    duplicate_history.append({
                        'order_id': order_id,
                        'email_type': email_type,
                        'email_type_display': latest_log.get_email_type_display(),
                        'sent_at': latest_log.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                        'payment_amount': str(latest_log.payment_amount),
                        'recipient_email': latest_log.recipient_email or request_obj.email,
                        'send_count': previous_logs.count()
                    })

        # 프로세스 2: Request ID 기반 (초안/최종안)
        elif email_type in ['draft_guide', 'final_draft_guide']:
            request_ids = request.data.get('request_ids', [])

            if not request_ids:
                return Response({'error': '선택된 요청이 없습니다.'}, status=status.HTTP_400_BAD_REQUEST)

            for request_id in request_ids:
                # Request ID + email_type만으로 체크 (payment_amount 불필요)
                previous_logs = SendLog.objects.filter(
                    sent_request_id=request_id,
                    email_type=email_type,
                    success=True
                ).order_by('-created_at')

                if previous_logs.exists():
                    latest_log = previous_logs.first()
                    duplicate_history.append({
                        'request_id': request_id,
                        'email_type': email_type,
                        'email_type_display': latest_log.get_email_type_display(),
                        'sent_at': latest_log.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                        'recipient_email': latest_log.recipient_email,
                        'send_count': previous_logs.count()
                    })

        return Response({
            'has_duplicate': len(duplicate_history) > 0,
            'duplicate_history': duplicate_history
        })

    except Exception as e:
        logger.error(f'[check_send_history] 오류: {str(e)}')
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
