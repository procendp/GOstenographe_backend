#!/usr/bin/env python
"""
sokgijung 최고 권한 관리자 계정 생성 스크립트
"""
import os
import sys
import django

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

def create_sokgijung_admin():
    """sokgijung 최고 권한 계정 생성 또는 업데이트"""
    username = 'sokgijung'
    password = 'minj0828!'
    email = 'sokgijung@gmail.com'

    try:
        # 기존 계정 확인
        user = User.objects.get(username=username)
        print(f"기존 {username} 계정 발견")

        # 비밀번호 및 권한 업데이트
        user.set_password(password)
        user.is_staff = True
        user.is_superuser = True
        user.is_admin = True
        user.email = email
        user.save()
        print(f"{username} 계정 업데이트 완료")

    except User.DoesNotExist:
        # 새 계정 생성
        user = User.objects.create_user(
            username=username,
            password=password,
            email=email,
            is_staff=True,
            is_superuser=True,
            is_admin=True
        )
        print(f"새 {username} 최고 권한 계정 생성 완료")

    print(f"\n{'='*50}")
    print(f"sokgijung 관리자 계정 정보:")
    print(f"  아이디: {username}")
    print(f"  비밀번호: {password}")
    print(f"  이메일: {email}")
    print(f"  권한: 슈퍼유저 (최고 권한)")
    print(f"{'='*50}\n")

if __name__ == '__main__':
    create_sokgijung_admin()
