from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RequestViewSet, TemplateViewSet, SendLogViewSet, S3PresignedURLView, S3DeleteView
from . import views

router = DefaultRouter()
router.register(r'requests', RequestViewSet)
router.register(r'templates', TemplateViewSet)
router.register(r'send-logs', SendLogViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('s3/presigned-url/', S3PresignedURLView.as_view(), name='s3-presigned-url'),
    path('s3/delete/', S3DeleteView.as_view(), name='s3-delete'),
] 