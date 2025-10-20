from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
from django.contrib.admin.views.decorators import staff_member_required
from requests.models import Request, File
import boto3
from django.conf import settings
import logging
import json
from django.db import transaction
import re

logger = logging.getLogger(__name__)

def format_final_option(final_option):
    """최종본 옵션 표시 형식을 개선합니다."""
    option_map = {
        'file': '파일',
        'file_post': '파일 + 등기 우편 (+5,000원)',
        'file_post_cd': '파일 + 등기 우편 + CD (+6,000원)',
        'file_post_usb': '파일 + 등기 우편 + USB (+10,000원)'
    }
    return option_map.get(final_option, final_option)

def format_phone_number(phone):
    """연락처 표시 형식을 개선합니다. (010-5590-7193 형태)"""
    if not phone:
        return phone
    
    # 숫자만 추출
    digits = re.sub(r'\D', '', phone)
    
    # 010으로 시작하는 11자리 번호인 경우
    if len(digits) == 11 and digits.startswith('010'):
        return f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"
    
    # 010으로 시작하는 10자리 번호인 경우 (중간 3자리)
    if len(digits) == 10 and digits.startswith('010'):
        return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
    
    # 다른 형식은 그대로 반환
    return phone

@staff_member_required
@require_GET
def get_order_file_counts(request):
    """Order ID별 파일 개수와 파일 목록을 반환하는 API"""
    try:
        order_ids = request.GET.get('order_ids', '').split(',')
        order_ids = [oid.strip() for oid in order_ids if oid.strip()]
        
        if not order_ids:
            return JsonResponse({'error': 'Order ID가 필요합니다.'}, status=400)
        
        file_counts = {}
        file_lists = {}
        
        for order_id in order_ids:
            # Order ID에 해당하는 모든 Request 조회
            requests = Request.objects.filter(order_id=order_id, is_temporary=False)
            
            total_files = 0
            file_list = []
            
            for request_obj in requests:
                # 첨부 파일들
                attachment_files = request_obj.files.all()
                for file_instance in attachment_files:
                    file_name = file_instance.original_name or file_instance.file.split('/')[-1]
                    file_list.append({
                        'name': file_name,
                        'type': '첨부파일'
                    })
                    total_files += 1
                
                # 속기록 파일
                if request_obj.transcript_file:
                    transcript_name = request_obj.transcript_file.original_name or request_obj.transcript_file.file.split('/')[-1]
                    file_list.append({
                        'name': transcript_name,
                        'type': '속기록'
                    })
                    total_files += 1
            
            file_counts[order_id] = total_files
            file_lists[order_id] = file_list
        
        return JsonResponse({
            'file_counts': file_counts,
            'file_lists': file_lists
        })
        
    except Exception as e:
        logger.error(f'[get_order_file_counts] 오류: {str(e)}')
        return JsonResponse({'error': str(e)}, status=500)

@staff_member_required
@require_POST
@csrf_exempt
def delete_orders(request):
    """
    선택된 Order ID들을 삭제합니다.
    - Order ID에 해당하는 모든 Request 삭제
    - 연관된 S3 파일 삭제
    - DB에서 File 및 Request 삭제
    """
    try:
        data = json.loads(request.body)
        order_ids = data.get('order_ids', [])

        if not order_ids:
            return JsonResponse({'error': '선택된 주문이 없습니다.'}, status=400)

        logger.info(f'[delete_orders] 삭제 요청 - Order IDs: {order_ids}')

        # S3 클라이언트 생성
        try:
            s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_S3_REGION_NAME
            )
            logger.info('[delete_orders] S3 클라이언트 생성 성공')
        except Exception as e:
            logger.error(f'[delete_orders] S3 클라이언트 생성 실패: {str(e)}')
            return JsonResponse({'error': f'S3 클라이언트 생성 실패: {str(e)}'}, status=500)

        deleted_orders_count = 0
        deleted_requests_count = 0
        deleted_files_count = 0
        errors = []

        for order_id in order_ids:
            try:
                # Order ID에 해당하는 모든 Request 조회
                requests = Request.objects.filter(order_id=order_id, is_temporary=False)

                if not requests.exists():
                    errors.append(f'Order ID {order_id}: 주문을 찾을 수 없습니다.')
                    continue

                order_request_count = requests.count()
                order_file_count = 0

                # 각 Request의 파일들 S3에서 삭제
                for request_obj in requests:
                    # 첨부 파일들 삭제
                    files = request_obj.files.all()
                    for file_instance in files:
                        try:
                            logger.info(f'[delete_orders] S3 첨부 파일 삭제 시도 - Key: {file_instance.file}')
                            s3_client.delete_object(
                                Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                                Key=file_instance.file
                            )
                            logger.info(f'[delete_orders] S3 첨부 파일 삭제 성공 - Key: {file_instance.file}')
                            order_file_count += 1
                        except Exception as e:
                            logger.error(f'[delete_orders] S3 첨부 파일 삭제 실패 - Key: {file_instance.file}, Error: {str(e)}')
                            # S3 삭제 실패해도 계속 진행
                    
                    # 속기록 파일 삭제
                    if request_obj.transcript_file:
                        try:
                            logger.info(f'[delete_orders] S3 속기록 파일 삭제 시도 - Key: {request_obj.transcript_file.file}')
                            s3_client.delete_object(
                                Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                                Key=request_obj.transcript_file.file
                            )
                            logger.info(f'[delete_orders] S3 속기록 파일 삭제 성공 - Key: {request_obj.transcript_file.file}')
                            order_file_count += 1
                        except Exception as e:
                            logger.error(f'[delete_orders] S3 속기록 파일 삭제 실패 - Key: {request_obj.transcript_file.file}, Error: {str(e)}')
                            # S3 삭제 실패해도 계속 진행

                # DB에서 Request 삭제 (CASCADE로 File도 자동 삭제)
                requests.delete()

                deleted_orders_count += 1
                deleted_requests_count += order_request_count
                deleted_files_count += order_file_count

                logger.info(f'[delete_orders] Order ID {order_id} 삭제 완료 - Requests: {order_request_count}, Files: {order_file_count}')

            except Exception as e:
                logger.error(f'[delete_orders] Order ID {order_id} 삭제 실패: {str(e)}')
                errors.append(f'Order ID {order_id}: {str(e)}')

        response_data = {
            'success': True,
            'message': f'{deleted_orders_count}개 주문 삭제 완료 (총 {deleted_requests_count}개 요청, {deleted_files_count}개 파일)',
            'deleted_orders': deleted_orders_count,
            'deleted_requests': deleted_requests_count,
            'deleted_files': deleted_files_count
        }

        if errors:
            response_data['errors'] = errors

        return JsonResponse(response_data)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON 파싱 실패'}, status=400)
    except Exception as e:
        logger.error(f'[delete_orders] 예외 발생: {str(e)}')
        return JsonResponse({'error': str(e)}, status=500)


@staff_member_required
@require_GET
@csrf_exempt
def generate_db_order_id(request):
    """
    DB 주문서용 Order ID와 Request ID 생성
    """
    try:
        # DB Order ID 생성
        order_id = Request.generate_order_id(is_db_order=True)
        request_id = Request.generate_request_id(order_id)

        return JsonResponse({
            'success': True,
            'order_id': order_id,
            'request_id': request_id
        })
    except Exception as e:
        logger.error(f'[generate_db_order_id] 예외 발생: {str(e)}')
        return JsonResponse({'error': str(e)}, status=500)


@staff_member_required
@require_POST
@csrf_exempt
def create_db_order(request):
    """
    DB 주문서 생성
    - DB Order ID 자동 생성
    - Request ID 자동 생성
    - 이메일 발송 안 함
    """
    try:
        data = json.loads(request.body)

        logger.info(f'[create_db_order] 요청 데이터: {data}')
        logger.info(f'[create_db_order] files 데이터: {data.get("files", [])}')

        # 필수 필드 검증
        required_fields = ['name', 'email', 'phone']
        for field in required_fields:
            if not data.get(field):
                return JsonResponse({'error': f'{field}은(는) 필수 항목입니다.'}, status=400)

        # DB Order ID 생성 (자동)
        order_id = Request.generate_order_id(is_db_order=True)

        # 트랜잭션 시작
        with transaction.atomic():
            # 기본 주문자 정보 (모든 Request에 공통으로 사용)
            base_request_data = {
                'order_id': order_id,
                'name': data.get('name'),
                'email': data.get('email'),
                'phone': data.get('phone'),
                'address': data.get('address', ''),
                'draft_format': data.get('draft_format', 'hwp'),
                'final_option': data.get('final_option', 'file'),
                'payment_status': data.get('payment_status', False),
                'payment_amount': data.get('payment_amount'),
                'notes': data.get('notes', ''),
                'is_temporary': False  # DB 주문은 정식 주문
            }

            # 파일 정보 처리 - 각 파일별로 개별 Request 생성 (프론트엔드와 동일한 로직)
            files_data = data.get('files_data', [])
            
            
            created_requests = []
            created_files = []

            for i, file_data in enumerate(files_data):
                
                
                # 각 파일별로 개별 Request 생성 (파일별 설정 포함)
                request_data = base_request_data.copy()
                
                # 파일별 설정 데이터 추가
                request_data.update({
                    'recording_type': file_data.get('recording_type', '전체'),
                    'partial_range': file_data.get('partial_range', ''),
                    'total_duration': file_data.get('total_duration', ''),
                    'speaker_count': file_data.get('speaker_count', 1),
                    'speaker_names': file_data.get('speaker_names', ''),
                    'recording_date': file_data.get('recording_date') or None,  # 빈 문자열을 None으로 변환
                    'additional_info': file_data.get('additional_info', ''),
                })
                
                request_instance = Request(**request_data)
                request_instance.save(skip_auto_email=True)
                
                
                
                # 해당 파일을 개별 Request에 연결
                file_key = file_data.get('file_key')
                if file_key:
                    
                    file_instance = File.objects.create(
                        request=request_instance,
                        file=file_key,
                        original_name=file_data.get('original_name', ''),
                        file_type=file_data.get('file_type', ''),
                        file_size=file_data.get('file_size', 0)
                    )
                    created_files.append({
                        'file_key': file_instance.file,
                        'original_name': file_instance.original_name,
                        'request_id': request_instance.request_id
                    })
                    created_requests.append({
                        'request_id': request_instance.request_id,
                        'order_id': request_instance.order_id
                    })
                    
                else:
                    logger.warning(f'[create_db_order] 파일 {i+1}에 file_key가 없음')

            logger.info(f'[create_db_order] DB 주문 생성 완료 - Order ID: {order_id}, Request 수: {len(created_requests)}, 파일 수: {len(created_files)}')

            return JsonResponse({
                'success': True,
                'message': f'DB 주문서가 생성되었습니다. ({len(created_requests)}개의 요청)',
                'order_id': order_id,
                'requests': created_requests,
                'files': created_files
            })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON 파싱 실패'}, status=400)
    except Exception as e:
        logger.error(f'[create_db_order] 예외 발생: {str(e)}')
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)


@staff_member_required
@require_POST
@csrf_exempt
def delete_uploaded_files(request):
    """
    업로드된 파일들을 S3와 DB에서 삭제
    """
    try:
        data = json.loads(request.body)
        file_keys = data.get('file_keys', [])
        
        
        if not file_keys:
            return JsonResponse({'error': '삭제할 파일이 없습니다.'}, status=400)
        
        deleted_files = []
        failed_files = []
        
        for file_key in file_keys:
            try:
                # S3에서 파일 삭제
                s3_client = boto3.client('s3', region_name=settings.AWS_S3_REGION_NAME)
                s3_client.delete_object(
                    Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                    Key=file_key
                )
                
                # DB에서 파일 정보 삭제 (연결되지 않은 파일들)
                File.objects.filter(file=file_key, request__isnull=True).delete()
                
                deleted_files.append(file_key)
                logger.info(f'[delete_uploaded_files] 파일 삭제 완료: {file_key}')
                
            except Exception as e:
                failed_files.append({'file_key': file_key, 'error': str(e)})
                logger.error(f'[delete_uploaded_files] 파일 삭제 실패: {file_key}, 오류: {str(e)}')
        
        return JsonResponse({
            'success': True,
            'deleted_files': deleted_files,
            'failed_files': failed_files,
            'message': f'{len(deleted_files)}개 파일이 삭제되었습니다.'
        })
        
    except Exception as e:
        logger.error(f'[delete_uploaded_files] 오류 발생: {str(e)}')
        return JsonResponse({'error': '파일 삭제 중 오류가 발생했습니다.'}, status=500)


# 공개 엔드포인트: apply 페이지에서 업로드 임시 파일 정리용 (S3 + DB 동시 삭제)
# 주의: 민감 데이터가 없고, file_key만으로 제한. 필요 시 추가 토큰 검증 가능
@require_POST
@csrf_exempt
def public_delete_uploaded_files(request):
    try:
        data = json.loads(request.body)
        file_keys = data.get('file_keys', [])

        if not file_keys:
            return JsonResponse({'error': '삭제할 파일이 없습니다.'}, status=400)

        deleted_files = []
        failed_files = []

        for file_key in file_keys:
            try:
                # S3에서 파일 삭제
                s3_client = boto3.client('s3', region_name=settings.AWS_S3_REGION_NAME)
                s3_client.delete_object(
                    Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                    Key=file_key
                )

                # DB에서 파일 정보 삭제 (아직 Request에 연결되지 않은 임시 파일만 안전 삭제)
                File.objects.filter(file=file_key, request__isnull=True).delete()

                deleted_files.append(file_key)
                logger.info(f'[public_delete_uploaded_files] 파일 삭제 완료: {file_key}')

            except Exception as e:
                failed_files.append({'file_key': file_key, 'error': str(e)})
                logger.error(f'[public_delete_uploaded_files] 파일 삭제 실패: {file_key}, 오류: {str(e)}')

        return JsonResponse({
            'success': True,
            'deleted_files': deleted_files,
            'failed_files': failed_files,
            'message': f'{len(deleted_files)}개 파일이 삭제되었습니다.'
        })

    except Exception as e:
        logger.error(f'[public_delete_uploaded_files] 오류 발생: {str(e)}')
        return JsonResponse({'error': '파일 삭제 중 오류가 발생했습니다.'}, status=500)
