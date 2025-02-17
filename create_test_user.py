import os
import sys

# 현재 디렉토리를 Python 경로에 추가
current_dir = os.path.abspath(os.path.dirname(__file__))
sys.path.append(current_dir)

from app import db, create_app
from app.models import User
from datetime import datetime

def create_test_user():
    app = create_app()
    with app.app_context():
        # 테스트 계정 정보
        test_username = 'test'
        test_password = 'Test1234!'
        test_email = 'test@wrsoft.co.kr'
        
        # 기존 테스트 계정 확인
        test_user = User.query.filter_by(username=test_username).first()
        if test_user:
            print(f'테스트 계정({test_username})이 이미 존재합니다.')
            return
            
        # 테스트 계정 생성
        test_user = User(
            username=test_username,
            email=test_email,
            name='테스트',
            phone='010-0000-0000',
            is_active=True,
            is_admin=False,
            created_at=datetime.now()
        )
        test_user.set_password(test_password)
        
        try:
            db.session.add(test_user)
            db.session.commit()
            print('테스트 계정이 성공적으로 생성되었습니다.')
            print(f'아이디: {test_username}')
            print(f'비밀번호: {test_password}')
            print(f'이메일: {test_email}')
        except Exception as e:
            print(f'테스트 계정 생성 중 오류가 발생했습니다: {str(e)}')
            db.session.rollback()

if __name__ == '__main__':
    create_test_user() 