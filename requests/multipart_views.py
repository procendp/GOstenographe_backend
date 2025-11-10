"""
S3 Multipart Upload API Views
대용량 파일을 효율적으로 업로드하기 위한 Multipart Upload 엔드포인트
"""
import boto3
import uuid
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.conf import settings

logger = logging.getLogger(__name__)


class MultipartUploadInitView(APIView):
    """Multipart Upload 초기화"""
    permission_classes = [AllowAny]
    authentication_classes = []

    MAX_FILE_SIZE = 3 * 1024 * 1024 * 1024  # 3GB
    ALLOWED_EXTENSIONS = {
        # 음성 파일
        'mp3', 'wav', 'm4a', 'cda', 'mod', 'ogg', 'wma', 'flac', 'asf',
        # 영상 파일
        'avi', 'mp4', 'wmv', 'm2v', 'mpeg', 'dpg', 'mts', 'webm', 'divx', 'amv'
    }

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

            # 파일 크기 체크
            try:
                file_size_int = int(file_size)
            except Exception:
                return Response(
                    {'error': 'file_size는 숫자여야 합니다.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

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

            # 고유 파일명 생성
            unique_file_name = f"{uuid.uuid4()}_{file_name}"

            # Multipart Upload 초기화
            multipart_upload = s3_client.create_multipart_upload(
                Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                Key=unique_file_name,
                ContentType=file_type
            )

            upload_id = multipart_upload['UploadId']

            logger.info(f'[MultipartUploadInit] 성공 - File: {unique_file_name}, UploadId: {upload_id}')

            return Response({
                'upload_id': upload_id,
                'file_key': unique_file_name
            })

        except Exception as e:
            logger.error(f'[MultipartUploadInit] 실패: {str(e)}')
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MultipartUploadPartView(APIView):
    """Multipart Upload - Part별 Presigned URL 생성"""
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        try:
            file_key = request.data.get('file_key')
            upload_id = request.data.get('upload_id')
            part_number = request.data.get('part_number')

            if not file_key or not upload_id or not part_number:
                return Response(
                    {'error': 'file_key, upload_id, part_number는 필수입니다.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # S3 클라이언트 생성
            s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_S3_REGION_NAME
            )

            # Part 업로드용 Presigned URL 생성
            presigned_url = s3_client.generate_presigned_url(
                'upload_part',
                Params={
                    'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
                    'Key': file_key,
                    'UploadId': upload_id,
                    'PartNumber': int(part_number)
                },
                ExpiresIn=3600  # 1시간
            )

            return Response({
                'presigned_url': presigned_url,
                'part_number': part_number
            })

        except Exception as e:
            logger.error(f'[MultipartUploadPart] 실패: {str(e)}')
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MultipartUploadCompleteView(APIView):
    """Multipart Upload 완료"""
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        try:
            file_key = request.data.get('file_key')
            upload_id = request.data.get('upload_id')
            parts = request.data.get('parts')  # [{'PartNumber': 1, 'ETag': 'xxx'}, ...]

            if not file_key or not upload_id or not parts:
                return Response(
                    {'error': 'file_key, upload_id, parts는 필수입니다.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # S3 클라이언트 생성
            s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_S3_REGION_NAME
            )

            # Multipart Upload 완료
            result = s3_client.complete_multipart_upload(
                Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                Key=file_key,
                UploadId=upload_id,
                MultipartUpload={'Parts': parts}
            )

            logger.info(f'[MultipartUploadComplete] 성공 - File: {file_key}')

            return Response({
                'success': True,
                'file_key': file_key,
                'location': result.get('Location')
            })

        except Exception as e:
            logger.error(f'[MultipartUploadComplete] 실패: {str(e)}')
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MultipartUploadAbortView(APIView):
    """Multipart Upload 취소"""
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        try:
            file_key = request.data.get('file_key')
            upload_id = request.data.get('upload_id')

            if not file_key or not upload_id:
                return Response(
                    {'error': 'file_key, upload_id는 필수입니다.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # S3 클라이언트 생성
            s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_S3_REGION_NAME
            )

            # Multipart Upload 취소
            s3_client.abort_multipart_upload(
                Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                Key=file_key,
                UploadId=upload_id
            )

            logger.info(f'[MultipartUploadAbort] 성공 - File: {file_key}')

            return Response({'success': True})

        except Exception as e:
            logger.error(f'[MultipartUploadAbort] 실패: {str(e)}')
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
