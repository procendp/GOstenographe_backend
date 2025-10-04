"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth.views import LogoutView
from django.views.generic import RedirectView
from rest_framework.routers import DefaultRouter
from requests.views import RequestViewSet, S3PresignedURLView, download_file_view, statistics_dashboard_view, statistics_api_view
from core.views import UserViewSet, CustomLoginView
from django.shortcuts import redirect
from django.contrib.auth import logout
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test, login_required
from django.shortcuts import redirect
from django.conf import settings
from django.http import JsonResponse
from django.conf.urls.static import static

def custom_logout(request):
    logout(request)
    messages.info(request, '로그아웃되었습니다.')
    return redirect('/login')

# 기존 AdminSite를 상속받아 커스텀 기능 추가
admin.site.__class__ = type('CustomAdminSite', (admin.site.__class__,), {
    'has_permission': lambda self, request: (
        False if not request.user.is_authenticated 
        and request.path.startswith('/admin/') 
        and not request.path.startswith('/admin/login/') 
        and messages.warning(request, '관리자 페이지에 접근하기 위해서는 로그인이 필요합니다.')
        else super(admin.site.__class__, self).has_permission(request)
    )
})

router = DefaultRouter()
router.register(r'requests', RequestViewSet)
router.register(r'auth', UserViewSet, basename='auth')

@login_required
def check_admin(request):
    if request.user.is_staff:
        return JsonResponse({'status': 'authenticated'})
    return JsonResponse({'status': 'unauthorized'}, status=401)

urlpatterns = [
    path('login/', CustomLoginView.as_view(), name='login'),
    path('admin/logout/', custom_logout, name='admin_logout'),
    path('manage/dashboard/', statistics_dashboard_view, name='statistics-dashboard'),
    path('api/statistics/', statistics_api_view, name='statistics-api'),
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api/', include('requests.urls')),
    path('api/check-admin/', check_admin, name='check-admin'),
    path('api/s3/presigned-url/', S3PresignedURLView.as_view(), name='s3-presigned-url'),
    path('api/download-file/', download_file_view, name='download-file'),
    path('', RedirectView.as_view(url='/admin/', permanent=False)),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
