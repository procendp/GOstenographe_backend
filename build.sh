#!/bin/bash

# Django 프로덕션 빌드 스크립트

echo "=== Django 빌드 시작 ==="

# Python 패키지 설치
echo "패키지 설치 중..."
pip install -r requirements.txt

# 정적 파일 수집
echo "정적 파일 수집 중..."
python manage.py collectstatic --noinput

# 데이터베이스 마이그레이션
echo "데이터베이스 마이그레이션 중..."
python manage.py migrate --noinput

# 배포 환경에 admin 계정 생성
echo "admin 계정 생성 중..."
python create_admin.py

echo "=== 빌드 완료 ==="
