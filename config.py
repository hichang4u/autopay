import os
from dotenv import load_dotenv
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'hard-to-guess-string'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'wrsoft.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # SMTP 설정
    SMTP_SERVER = os.environ.get('SMTP_SERVER') or 'smtp.gmail.com'
    SMTP_PORT = int(os.environ.get('SMTP_PORT') or 587)
    SMTP_USERNAME = os.environ.get('SMTP_USERNAME')
    SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD')
    
    # 세션 설정
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)  # 일반 세션 유효 시간
    REMEMBER_COOKIE_DURATION = timedelta(days=30)    # 로그인 상태 유지 시 쿠키 유효 시간
    REMEMBER_COOKIE_SECURE = False                   # 개발 환경에서는 HTTP 허용
    REMEMBER_COOKIE_HTTPONLY = True                  # JavaScript에서 remember 쿠키 접근 방지
    REMEMBER_COOKIE_SAMESITE = 'Lax'                # CSRF 방지
    
    # 보안 설정
    WTF_CSRF_ENABLED = True  # CSRF 보호 활성화
    WTF_CSRF_TIME_LIMIT = 3600  # CSRF 토큰 유효 시간 (초)
    
    # 로그인 보안 설정
    MAX_LOGIN_ATTEMPTS = 5  # 최대 로그인 시도 횟수
    LOGIN_DISABLED = False  # 로그인 기능 활성화
    
    # 세션 보안 설정
    SESSION_COOKIE_SECURE = False  # 개발 환경에서는 HTTP 허용
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'