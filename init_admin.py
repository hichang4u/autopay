from app import db, create_app
from app.models import User
from datetime import datetime
import os
from dotenv import load_dotenv

def init_admin():
    app = create_app()
    with app.app_context():
        # 환경 변수에서 관리자 정보 가져오기
        admin_username = os.environ.get('ADMIN_USERNAME')
        admin_password = os.environ.get('ADMIN_PASSWORD')
        admin_email = os.environ.get('ADMIN_EMAIL')

        # 환경 변수 검증
        if not all([admin_username, admin_password, admin_email]):
            print('오류: 관리자 계정 정보가 환경 변수에 모두 설정되지 않았습니다.')
            print('필요한 환경 변수: ADMIN_USERNAME, ADMIN_PASSWORD, ADMIN_EMAIL')
            return
            
        # 기존 관리자 확인
        admin = User.query.filter_by(username=admin_username).first()
        if admin:
            print(f'관리자 계정({admin_username})이 이미 존재합니다.')
            return
            
        # 관리자 계정 생성
        admin = User(
            username=admin_username,
            email=admin_email,
            is_active=True,
            is_admin=True,
            created_at=datetime.now()
        )
        admin.set_password(admin_password)
        
        try:
            db.session.add(admin)
            db.session.commit()
            print('관리자 계정이 성공적으로 생성되었습니다.')
            print(f'아이디: {admin_username}')
            print(f'이메일: {admin_email}')
            print('비밀번호: 환경 변수 ADMIN_PASSWORD 값')
        except Exception as e:
            print(f'관리자 계정 생성 중 오류가 발생했습니다: {str(e)}')
            db.session.rollback()

if __name__ == '__main__':
    # 환경 변수 로드
    load_dotenv()
    init_admin() 