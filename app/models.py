from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from pytz import timezone

def get_korea_time():
    return datetime.now(timezone('Asia/Seoul'))

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    email = db.Column(db.String(120), unique=True)
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)  # 관리자 권한
    last_login = db.Column(db.DateTime)
    login_ip = db.Column(db.String(45))
    failed_login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, onupdate=datetime.now)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_locked(self):
        if self.locked_until and self.locked_until > datetime.now():
            return True
        return False

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))

class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    emp_number = db.Column(db.String(20), unique=True, nullable=False)  # 사번
    name = db.Column(db.String(100), nullable=False)  # 이름
    birth_date = db.Column(db.Date)  # 생년월일
    join_date = db.Column(db.Date)  # 입사일
    position = db.Column(db.String(50))  # 직위
    email = db.Column(db.String(120), unique=True)
    pdf_password = db.Column(db.String(100))

    # 생성 정보
    created_at = db.Column(db.DateTime, default=get_korea_time)
    created_by = db.Column(db.String(80))  # 생성자 username
    created_ip = db.Column(db.String(45))  # IPv6까지 고려한 길이
    
    # 수정 정보
    updated_at = db.Column(db.DateTime, onupdate=get_korea_time)
    updated_by = db.Column(db.String(80))  # 수정자 username
    updated_ip = db.Column(db.String(45))  # IPv6까지 고려한 길이
    
    def to_dict(self):
        """직원 정보를 딕셔너리로 변환"""
        return {
            'id': self.id,
            'emp_number': self.emp_number,
            'name': self.name,
            'birth_date': self.birth_date.strftime('%Y-%m-%d') if self.birth_date else '',
            'join_date': self.join_date.strftime('%Y-%m-%d') if self.join_date else '',
            'position': self.position,
            'email': self.email,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'created_by': self.created_by,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else '',
            'updated_by': self.updated_by
        }

    def record_history(self, field_name, old_value, new_value, user, ip_address):
        """변경 이력 기록"""
        history = EmployeeHistory(
            employee_id=self.id,
            field_name=field_name,
            old_value=str(old_value) if old_value is not None else '',
            new_value=str(new_value) if new_value is not None else '',
            changed_by=user,
            changed_ip=ip_address
        )
        db.session.add(history)

class Salary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    emp_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    payment_date = db.Column(db.Date, nullable=False)  # 지급일
    base_salary = db.Column(db.Integer)  # 기본급
    position_bonus = db.Column(db.Integer)  # 직책수당
    overtime_pay = db.Column(db.Integer)  # 연장근로수당
    meal_allowance = db.Column(db.Integer)  # 식대
    # ... 기타 급여 항목들
    
    employee = db.relationship('Employee', backref='salaries') 

class PayrollRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pay_year_month = db.Column(db.String(7), nullable=False)  # YYYY-MM 형식
    payment_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default='임시저장')  # 임시저장, 완료
    
    # 생성 정보
    created_at = db.Column(db.DateTime, default=get_korea_time)
    created_by = db.Column(db.String(80))  # 생성자 username
    created_ip = db.Column(db.String(45))  # IPv6까지 고려한 길이
    
    # 수정 정보
    updated_at = db.Column(db.DateTime, onupdate=get_korea_time)
    updated_by = db.Column(db.String(80))  # 수정자 username
    updated_ip = db.Column(db.String(45))  # IPv6까지 고려한 길이
    
    details = db.relationship('PayrollDetail', backref='record', lazy=True)

class PayrollDetail(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    record_id = db.Column(db.Integer, db.ForeignKey('payroll_record.id'), nullable=False)
    employee_id = db.Column(db.String(20), nullable=False)
    employee_name = db.Column(db.String(100), nullable=False)
    department = db.Column(db.String(100))
    position = db.Column(db.String(100))
    
    # 지급 항목
    base_salary = db.Column(db.Integer, default=0)  # 기본급
    position_allowance = db.Column(db.Integer, default=0)  # 직책수당
    meal_allowance = db.Column(db.Integer, default=0)  # 식대
    car_allowance = db.Column(db.Integer, default=0)  # 자가운전보조금
    total_payment = db.Column(db.Integer, default=0)  # 지급액 계
    
    # 공제 항목
    income_tax = db.Column(db.Integer, default=0)  # 소득세
    local_income_tax = db.Column(db.Integer, default=0)  # 지방소득세
    national_pension = db.Column(db.Integer, default=0)  # 국민연금
    health_insurance = db.Column(db.Integer, default=0)  # 건강보험
    long_term_care = db.Column(db.Integer, default=0)  # 장기요양보험
    employment_insurance = db.Column(db.Integer, default=0)  # 고용보험
    total_deduction = db.Column(db.Integer, default=0)  # 공제액 계
    
    # 실수령액
    net_amount = db.Column(db.Integer, default=0)
    
    created_at = db.Column(db.DateTime, default=get_korea_time)

class EmployeeHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    field_name = db.Column(db.String(50), nullable=False)  # 변경된 필드명
    old_value = db.Column(db.String(200))  # 이전 값
    new_value = db.Column(db.String(200))  # 새로운 값
    changed_by = db.Column(db.String(80))  # 변경한 사용자
    changed_at = db.Column(db.DateTime, default=get_korea_time)  # 변경 시간
    changed_ip = db.Column(db.String(45))  # 변경한 IP

    employee = db.relationship('Employee', backref='history')