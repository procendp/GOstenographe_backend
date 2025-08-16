from django.shortcuts import render
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.shortcuts import get_object_or_404
from .models import Request, Template, SendLog, File
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

logger = logging.getLogger(__name__)

# Create your views here.

class RequestViewSet(viewsets.ModelViewSet):
    queryset = Request.objects.all()
    serializer_class = RequestSerializer
    parser_classes = (JSONParser, MultiPartParser, FormParser)
    permission_classes = [AllowAny]

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

    @action(detail=True, methods=['post'])
    def get_upload_url(self, request, pk=None):
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
                {'error': '파일 크기가 제한을 초과합니다. (최대 3GB)'},
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
    def upload_file(self, request, pk=None):
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
    def delete_file(self, request, pk=None):
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
    def files(self, request, pk=None):
        """
        해당 request에 업로드된 파일 리스트를 반환합니다.
        """
        request_obj = self.get_object()
        files = request_obj.files.all()
        serializer = FileSerializer(files, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
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

    # 허용 확장자 및 MIME 타입 목록
    ALLOWED_EXTENSIONS = {
        'txt', 'hwp', 'doc', 'docx', 'pdf', 'ppt', 'pptx', 'xls', 'xlsx',
        'mp3', 'mp4', 'asf', 'm4v', 'mov', 'wmv', 'avi', 'wav', 'zip'
    }
    ALLOWED_MIME_TYPES = {
        'text/plain', 'application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.ms-powerpoint', 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/zip', 'audio/mpeg', 'audio/wav', 'video/mp4', 'video/x-ms-asf', 'video/x-m4v', 'video/quicktime',
        'video/x-ms-wmv', 'video/x-msvideo', 'application/x-hwp',
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

            # 확장자 체크
            ext = file_name.split('.')[-1].lower()
            if ext not in self.ALLOWED_EXTENSIONS:
                return Response(
                    {'error': f'허용되지 않은 파일 확장자입니다. ({ext})'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # MIME 타입 체크
            if file_type not in self.ALLOWED_MIME_TYPES:
                return Response(
                    {'error': f'허용되지 않은 파일 타입입니다. ({file_type})'},
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

            # S3 클라이언트 생성
            s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_S3_REGION_NAME
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
