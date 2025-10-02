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
    path('send/quotation-guide/', views.send_quotation_guide, name='send-quotation-guide'),
    path('send/payment-completion-guide/', views.send_payment_completion_guide, name='send-payment-completion-guide'),
    path('send/draft-guide/', views.send_draft_guide, name='send-draft-guide'),
    path('send/final-draft-guide/', views.send_final_draft_guide, name='send-final-draft-guide'),
    path('send/application-completion-guide/', views.send_application_completion_guide, name='send-application-completion-guide'),
    path('send/check-history/', views.check_send_history, name='check-send-history'),
] 