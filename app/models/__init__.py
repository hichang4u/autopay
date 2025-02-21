from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from pytz import timezone

def get_korea_time():
    return datetime.now(timezone('Asia/Seoul'))

# 기존 모델들을 여기로 이동
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    name = db.Column(db.String(50))
    phone = db.Column(db.String(20))
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
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

    def __repr__(self):
        return f'<User {self.username}>'

# Employee 모델
class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    emp_number = db.Column(db.String(10), unique=True, nullable=False)
    name = db.Column(db.String(50), nullable=False)
    birth_date = db.Column(db.Date)
    join_date = db.Column(db.Date)
    position = db.Column(db.String(20))
    department = db.Column(db.String(50))
    email = db.Column(db.String(120), unique=True)
    pdf_password = db.Column(db.String(128))
    
    # 생성 정보
    created_at = db.Column(db.DateTime, default=get_korea_time)
    created_by = db.Column(db.String(80))
    created_ip = db.Column(db.String(45))
    
    # 수정 정보
    updated_at = db.Column(db.DateTime, onupdate=get_korea_time)
    updated_by = db.Column(db.String(80))
    updated_ip = db.Column(db.String(45))
    
    def to_dict(self):
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

# EmployeeHistory 모델
class EmployeeHistory(db.Model):
    """직원 정보 변경 이력"""
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    change_type = db.Column(db.String(20), nullable=False)  # INSERT, UPDATE, DELETE
    field_name = db.Column(db.String(50), nullable=False)
    old_value = db.Column(db.String(200))
    new_value = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=get_korea_time)
    created_by = db.Column(db.String(80))
    created_ip = db.Column(db.String(45))

    employee = db.relationship('Employee', backref=db.backref('history', lazy=True))

# PayrollRecord 모델
class PayrollRecord(db.Model):
    __tablename__ = 'payroll_record'
    
    id = db.Column(db.Integer, primary_key=True)
    pay_year_month = db.Column(db.String(7), nullable=False)  # YYYY-MM 형식
    payment_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default='TEMP_SAVE')
    
    created_at = db.Column(db.DateTime, default=get_korea_time)
    created_by = db.Column(db.String(80))
    created_ip = db.Column(db.String(45))
    updated_at = db.Column(db.DateTime, onupdate=get_korea_time)
    updated_by = db.Column(db.String(80))
    updated_ip = db.Column(db.String(45))
    
    details = db.relationship('PayrollDetail', backref='record', lazy=True)
    
    def __repr__(self):
        return f'<PayrollRecord {self.pay_year_month}>'

# PayrollDetail 모델
class PayrollDetail(db.Model):
    __tablename__ = 'payroll_detail'
    
    id = db.Column(db.Integer, primary_key=True)
    record_id = db.Column(db.Integer, db.ForeignKey('payroll_record.id', ondelete='CASCADE'), nullable=False)
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
    
    created_at = db.Column(db.DateTime, default=get_korea_time)
    updated_at = db.Column(db.DateTime, onupdate=get_korea_time)

# 다른 모델들도 필요에 따라 여기에 추가 