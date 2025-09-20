from requests.models import Request, File
import boto3
from django.conf import settings

print('=== 첨부파일 정보 확인 ===')
files = File.objects.all()
for f in files:
    print(f'File ID: {f.id}')
    print(f'  Request ID: {f.request.id}')
    print(f'  Original Name: {f.original_name}')
    print(f'  S3 Key: {f.file}')
    print(f'  File Type: {f.file_type}')
    print(f'  File Size: {f.file_size}')
    print()

print('=== S3 파일 존재 여부 확인 ===')
s3_client = boto3.client('s3')
bucket_name = settings.AWS_STORAGE_BUCKET_NAME

for f in files:
    try:
        response = s3_client.head_object(Bucket=bucket_name, Key=f.file)
        print(f'✓ {f.original_name}: S3에 존재함 (크기: {response["ContentLength"]} bytes)')
    except Exception as e:
        print(f'✗ {f.original_name}: S3에 없음 - {str(e)}')

print('\n=== S3 버킷 내용 확인 ===')
try:
    response = s3_client.list_objects_v2(Bucket=bucket_name, MaxKeys=10)
    if 'Contents' in response:
        print('S3 버킷의 파일들:')
        for obj in response['Contents']:
            print(f'  - {obj["Key"]} (크기: {obj["Size"]} bytes)')
    else:
        print('S3 버킷이 비어있습니다.')
except Exception as e:
    print(f'S3 버킷 접근 실패: {str(e)}')