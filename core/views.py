from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth import login, logout
from .models import User
from .serializers import UserSerializer, UserCreateSerializer
from django.http import HttpResponseRedirect
from django.contrib.auth.views import LoginView
from django.contrib import messages

# Create your views here.

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_permissions(self):
        if self.action == 'create':
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return UserSerializer

    @action(detail=False, methods=['post'])
    def login(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        
        try:
            user = User.objects.get(username=username)
            if user.check_password(password):
                login(request, user)
                return Response(UserSerializer(user).data)
            return Response(
                {'error': '비밀번호가 일치하지 않습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except User.DoesNotExist:
            return Response(
                {'error': '사용자를 찾을 수 없습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['post'])
    def logout(self, request):
        logout(request)
        response = HttpResponseRedirect('/admin/login/')
        response.delete_cookie('sessionid')
        response.delete_cookie('csrftoken')
        return response

    @action(detail=False, methods=['get'])
    def me(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

class CustomLoginView(LoginView):
    template_name = 'admin/login.html'
    redirect_authenticated_user = False  # 무한 루프 방지
    next_page = '/admin/'

    def form_invalid(self, form):
        messages.error(self.request, '아이디 또는 비밀번호가 올바르지 않습니다.')
        return super().form_invalid(form)
    
    def get_success_url(self):
        """로그인 성공 후 리다이렉트 URL"""
        return self.get_redirect_url() or '/admin/'
