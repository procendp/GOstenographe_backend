#!/bin/bash

# 8000번 포트를 사용하는 프로세스 찾기
PID=$(lsof -ti:8000)

# 프로세스가 있으면 종료
if [ ! -z "$PID" ]; then
    echo "포트 8000을 사용하는 프로세스(PID: $PID)를 종료합니다."
    kill -9 $PID
    sleep 1
fi

# Django 서버 시작
echo "Django 서버를 시작합니다..."
source venv/bin/activate
python manage.py runserver 8000 