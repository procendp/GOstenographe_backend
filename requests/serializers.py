from rest_framework import serializers
from .models import Request, Template, SendLog, File
import boto3
from django.conf import settings

class FileSerializer(serializers.ModelSerializer):
    presigned_url = serializers.SerializerMethodField()

    class Meta:
        model = File
        fields = ['id', 'file', 'created_at', 'original_name', 'presigned_url']
        read_only_fields = ('id', 'file', 'created_at', 'original_name', 'presigned_url')

    def get_presigned_url(self, obj):
        if not obj.file:
            return None
        try:
            s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_S3_REGION_NAME
            )
            url = s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
                    'Key': obj.file.name
                },
                ExpiresIn=60*10  # 10분
            )
            return url
        except Exception:
            return None

class RequestSerializer(serializers.ModelSerializer):
    files = FileSerializer(many=True, read_only=True)
    class Meta:
        model = Request
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')

class TemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Template
        fields = '__all__'
        read_only_fields = ('last_modified',)

class SendLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = SendLog
        fields = '__all__'
        read_only_fields = ('sent_at',) 