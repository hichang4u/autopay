from app import db, create_app
import sqlite3
import os

def init_db():
    app = create_app()
    
    # 데이터베이스 파일 경로
    db_path = 'wrsoft.db'
    
    # 기존 데이터베이스 백업
    if os.path.exists(db_path):
        print("기존 데이터베이스 백업 중...")
        os.rename(db_path, 'wrsoft_backup.db')
    
    with app.app_context():
        # 데이터베이스 테이블 생성
        db.create_all()
        print("데이터베이스 테이블이 생성되었습니다.")
        
        # 백업 데이터 복원 (있는 경우)
        if os.path.exists('wrsoft_backup.db'):
            try:
                # 백업 DB 연결
                backup_conn = sqlite3.connect('wrsoft_backup.db')
                backup_cur = backup_conn.cursor()
                
                # 현재 DB 연결
                conn = sqlite3.connect(db_path)
                cur = conn.cursor()
                
                # user 테이블 데이터 복원
                backup_cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user'")
                if backup_cur.fetchone():
                    print("기존 사용자 데이터 복원 중...")
                    backup_cur.execute("SELECT * FROM user")
                    users = backup_cur.fetchall()
                    
                    if users:
                        # 컬럼명 가져오기
                        columns = [description[0] for description in backup_cur.description]
                        
                        # INSERT 쿼리 생성
                        placeholders = ','.join(['?' for _ in columns])
                        insert_query = f"INSERT INTO user ({','.join(columns)}) VALUES ({placeholders})"
                        
                        # 데이터 삽입
                        cur.executemany(insert_query, users)
                        conn.commit()
                        print(f"{len(users)}개의 사용자 데이터가 복원되었습니다.")
                
                # 연결 종료
                backup_conn.close()
                conn.close()
                
                # 백업 파일 삭제
                os.remove('wrsoft_backup.db')
                print("백업 파일이 삭제되었습니다.")
                
            except Exception as e:
                print(f"데이터 복원 중 오류 발생: {str(e)}")
                print("새로운 데이터베이스로 시작합니다.")

if __name__ == '__main__':
    init_db() 