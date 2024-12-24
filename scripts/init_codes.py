from app import create_app, db
from app.models import CodeGroup, Code

# 초기 코드 그룹 데이터
code_groups = [
    {
        'group_code': 'PAYROLL_STATUS',
        'group_name': '급여처리상태',
        'description': '급여처리의 각 단계별 상태'
    }
]

# 초기 코드 데이터
codes = [
    # 급여처리상태
    {
        'group_code': 'PAYROLL_STATUS',
        'code': 'TEMP_SAVE',
        'name': '임시저장',
        'order_seq': 1,
        'extra_data': {
            'badge_style': 'bg-warning text-dark',
            'actions': ['view', 'delete', 'complete']
        }
    },
    {
        'group_code': 'PAYROLL_STATUS',
        'code': 'COMPLETE',
        'name': '완료',
        'order_seq': 2,
        'extra_data': {
            'badge_style': 'bg-success text-white',
            'actions': ['view', 'pdf']
        }
    },
    {
        'group_code': 'PAYROLL_STATUS',
        'code': 'PDF_GENERATED',
        'name': 'PDF생성',
        'order_seq': 3,
        'extra_data': {
            'badge_style': 'bg-info text-white',
            'actions': ['view', 'email']
        }
    },
    {
        'group_code': 'PAYROLL_STATUS',
        'code': 'EMAIL_SENT',
        'name': '발송완료',
        'order_seq': 4,
        'extra_data': {
            'badge_style': 'bg-primary text-white',
            'actions': ['view', 'pdf_view', 'resend']
        }
    }
]

def init_codes():
    app = create_app()
    with app.app_context():
        # 코드 그룹 생성
        for group in code_groups:
            code_group = CodeGroup(**group)
            db.session.add(code_group)
        db.session.commit()
        
        # 코드 생성
        for code in codes:
            code_entry = Code(**code)
            db.session.add(code_entry)
        db.session.commit()

if __name__ == '__main__':
    init_codes() 