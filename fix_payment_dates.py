import os
import sys
from datetime import datetime
from pytz import timezone

# 현재 디렉토리를 Python 경로에 추가
current_dir = os.path.abspath(os.path.dirname(__file__))
sys.path.append(current_dir)

from app import db, create_app
from app.models import PayrollRecord, get_korea_time

def fix_payment_dates():
    app = create_app()
    with app.app_context():
        try:
            # 잘못된 형식의 payment_date를 가진 레코드 조회
            records = PayrollRecord.query.all()
            fixed_count = 0
            
            for record in records:
                if record.payment_date:
                    try:
                        # 현재 한국 시간으로 설정
                        new_date = get_korea_time().date()
                        record.payment_date = new_date
                        fixed_count += 1
                        print(f"레코드 ID {record.id}: {record.payment_date} -> {new_date}")
                    except Exception as e:
                        print(f"오류: 레코드 ID {record.id}의 payment_date 변환 실패 - {str(e)}")
            
            if fixed_count > 0:
                db.session.commit()
                print(f"\n{fixed_count}개의 레코드가 수정되었습니다.")
            else:
                print("\n수정이 필요한 레코드가 없습니다.")
                
        except Exception as e:
            db.session.rollback()
            print(f"오류가 발생했습니다: {str(e)}")

if __name__ == '__main__':
    fix_payment_dates() 