#!/usr/bin/env python
"""
배포 환경에 admin 계정을 생성하는 스크립트
"""
import os
import sys
import django

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.core.management import execute_from_command_line

User = get_user_model()

def create_admin_user():
    """admin 계정 생성 또는 업데이트"""
    username = 'admin'
    password = 'admin1234'
    email = 'admin@gostenographe.com'
    
    try:
        # 기존 admin 계정 확인
        user = User.objects.get(username=username)
        print(f"기존 admin 계정 발견: {user.username}")
        
        # 비밀번호 업데이트
        user.set_password(password)
        user.is_staff = True
        user.is_superuser = True
        user.is_admin = True
        user.save()
        print(f"admin 계정 비밀번호 업데이트 완료")
        
    except User.DoesNotExist:
        # 새 admin 계정 생성
        user = User.objects.create_user(
            username=username,
            password=password,
            email=email,
            is_staff=True,
            is_superuser=True,
            is_admin=True
        )
        print(f"새 admin 계정 생성 완료: {user.username}")
    
    print(f"로그인 정보:")
    print(f"  아이디: {username}")
    print(f"  비밀번호: {password}")
    print(f"  이메일: {email}")

if __name__ == '__main__':
    create_admin_user()







