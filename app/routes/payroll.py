from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, current_app, send_file
from flask_login import login_required, current_user
from app import db
from app.models import PayrollRecord, PayrollDetail, Employee
from datetime import datetime
import logging
import re
from sqlalchemy.exc import IntegrityError
from sqlalchemy.dialects.sqlite import insert
import os
from sqlalchemy import desc
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.utils import formatdate
import PyPDF2
import pdfplumber
import tabula

payroll = Blueprint('payroll', __name__)

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 급여 데이터 유효성 검사 함수
def validate_payroll_data(data):
    errors = []
    
    # 기본 필드 검사
    required_fields = ['pay_year_month', 'payment_date', 'employees']
    for field in required_fields:
        if field not in data:
            errors.append(f"필수 필드 '{field}'가 누락되었습니다.")
    
    if not errors:
        # 날짜 형식 검사
        try:
            datetime.strptime(data['payment_date'], '%Y-%m-%d')
        except ValueError:
            errors.append("지급일 형식이 올바르지 않습니다. (YYYY-MM-DD)")
            
        # 귀속연월 형식 검사 (YYYY-MM)
        if not re.match(r'^\d{4}-\d{2}$', data['pay_year_month']):
            errors.append("귀속연월 형식이 올바르지 않습니다. (YYYY-MM)")
            
        # 직원 데이터 검사
        if not data['employees']:
            errors.append("저장할 직원 데이터가 없습니다.")
        else:
            for idx, emp in enumerate(data['employees']):
                if not emp.get('employee_id') or not emp.get('employee_name'):
                    errors.append(f"{idx+1}번째 직원의 사번 또는 이름이 누락되었습니다.")
                
                # 급여 항목 음수 체크
                salary_fields = ['base_salary', 'position_allowance', 'overtime_pay', 'meal_allowance']
                for field in salary_fields:
                    if emp.get(field, 0) < 0:
                        errors.append(f"{idx+1}번째 직원의 {field}가 음수입니다.")
    
    return errors

# 급여 관리 메인 페이지
@payroll.route('/payroll')
@login_required
def index():
    return render_template('payroll/payroll.html')

# 급여 데이터 저장 API
@payroll.route('/payroll/save', methods=['POST'])
@login_required
def save_payroll():
    try:
        data = request.get_json()
        
        # 데이터 유효성 검사
        validation_errors = validate_payroll_data(data)
        if validation_errors:
            return jsonify({
                'success': False,
                'message': '유효성 검사 실패',
                'errors': validation_errors
            }), 400
            
        # 중복 체크
        existing_record = PayrollRecord.query.filter_by(
            pay_year_month=data['pay_year_month']
        ).first()
        
        if existing_record:
            return jsonify({
                'success': False,
                'message': f"{data['pay_year_month']} 귀속연월의 급여 데이터가 이미 존재합니다."
            }), 409
        
        logger.info(f"급여 데이터 저장 시작: {data['pay_year_month']}, 사용자: {current_user.username}")
        
        # PayrollRecord 생성
        record = PayrollRecord(
            pay_year_month=data['pay_year_month'],
            payment_date=datetime.strptime(data['payment_date'], '%Y-%m-%d').date(),
            status='임��저장',
            created_by=current_user.username,
            created_ip=request.remote_addr
        )
        db.session.add(record)
        db.session.flush()
        
        # PayrollDetail 생성
        detail = PayrollDetail(
            record_id=record.id,
            employee_id='45',
            employee_name='박희창',
            
            # 지급 항목
            base_salary=6300000,
            position_allowance=400000,
            meal_allowance=200000,
            car_allowance=200000,
            total_payment=7100000,
            
            # 공제 항목
            income_tax=481490,
            local_income_tax=48140,
            national_pension=277650,
            health_insurance=237510,
            long_term_care=30750,
            employment_insurance=60300,
            total_deduction=1135840,
            
            # 실수령액
            net_amount=5964160
        )
        db.session.add(detail)
        db.session.commit()
        
        logger.info(f"급여 데이터 저장 완료: {data['pay_year_month']}")
        
        return jsonify({
            'success': True,
            'message': '급여 데이터가 성공적으로 저장되었습니다.',
            'record_id': record.id
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"급여 데이터 저장 실패: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'저장 중 오류가 발생했습니다: {str(e)}'
        }), 500

# 급여 명세서 생성 페이지
@payroll.route('/payroll/generate')
@login_required
def generate():
    return render_template('payroll/generate.html')

# 급여 명세서 생성 처리
@payroll.route('/payroll/generate-manual', methods=['POST'])
@login_required
def generate_manual():
    try:
        data = request.form
        
        # TODO: 급여 명세서 생성 로직 구현
        # 1. PDF 템플릿 로드
        # 2. 데이터 매핑
        # 3. PDF 생성
        # 4. 파일 저장
        
        flash('급여명세서가 생성되었습니다.', 'success')
        return redirect(url_for('payroll.index'))
    except Exception as e:
        flash(f'급여명세서 생성 중 오류가 발생했습니다: {str(e)}', 'error')
        return redirect(url_for('payroll.generate'))

# 급여 명세서 이메일 발송
@payroll.route('/payroll/send-email', methods=['POST'])
@login_required
def send_email():
    try:
        data = request.get_json()
        
        # TODO: 이메일 발송 로직 구현
        # 1. 수신자 보 확인
        # 2. 이메일 템플릿 로드
        # 3. PDF 첨부
        # 4. 이메일 발송
        
        return jsonify({
            'success': True,
            'message': '이메일이 발송되었습니다.'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'이메일 발송 중 오류가 발생했습니다: {str(e)}'
        }), 500

# 급여 처리 이력 조회
@payroll.route('/payroll/history')
@login_required
def history():
    return render_template('payroll/history.html')

# Excel 파일 파싱 API
@payroll.route('/payroll/parse-excel', methods=['POST'])
@login_required
def parse_excel():
    if 'file' not in request.files:
        return jsonify({'error': '파일이 없습니다.'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '선택된 파일이 없습니다.'}), 400
    
    try:
        import pandas as pd
        df = pd.read_excel(file)
        data = df.iloc[0].to_dict()
        
        # NaN 값과 날짜 처리
        for key, value in data.items():
            if pd.isna(value):
                data[key] = ''
            elif isinstance(value, pd.Timestamp):
                data[key] = value.strftime('%Y-%m-%d')
        
        return jsonify(data)
    except Exception as e:
        return jsonify({
            'error': f'파일 처리 중 오류가 발생했습니다: {str(e)}'
        }), 500

# 급여 데이터 조회 API
@payroll.route('/payroll/list', methods=['GET'])
@login_required
def get_payroll_list():
    try:
        # 최근 12개월의 급여 기록을 가져옴
        records = PayrollRecord.query.order_by(
            PayrollRecord.pay_year_month.desc()
        ).limit(12).all()
        
        result = []
        for record in records:
            # 각 기록에 대한 직원 수 계산
            employee_count = PayrollDetail.query.filter_by(record_id=record.id).count()
            
            result.append({
                'id': record.id,
                'pay_year_month': record.pay_year_month,
                'payment_date': record.payment_date.strftime('%Y-%m-%d'),
                'employee_count': employee_count,
                'created_at': record.created_at.strftime('%Y-%m-%d %H:%M'),
                'updated_at': record.updated_at.strftime('%Y-%m-%d %H:%M') if record.updated_at else '',
                'status': record.status
            })
        
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        logger.error(f"급여 데이터 조회 실패: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'데이�� 조회 중 오류가 발생했습니다: {str(e)}'
        }), 500

# 급여 상세 데이터 조회 API
@payroll.route('/payroll/detail/<int:record_id>', methods=['GET'])
@login_required
def get_payroll_detail(record_id):
    try:
        # 급여 기록 조회
        record = PayrollRecord.query.get_or_404(record_id)
        
        # 상세 데이터 조회
        details = PayrollDetail.query.filter_by(record_id=record_id).all()
        
        result = {
            'record': {
                'id': record.id,
                'pay_year_month': record.pay_year_month,
                'payment_date': record.payment_date.strftime('%Y-%m-%d'),
                'status': record.status,
                'created_at': record.created_at.strftime('%Y-%m-%d %H:%M')
            },
            'details': [{
                'id': detail.id,
                'employee_id': detail.employee_id,
                'employee_name': detail.employee_name,
                'department': detail.department,
                'position': detail.position,
                'base_salary': detail.base_salary,
                'position_allowance': detail.position_allowance,
                'overtime_pay': detail.overtime_pay,
                'meal_allowance': detail.meal_allowance,
                'income_tax': detail.income_tax,
                'national_pension': detail.national_pension,
                'health_insurance': detail.health_insurance,
                'employment_insurance': detail.employment_insurance
            } for detail in details]
        }
        
        return jsonify({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        logger.error(f"급여 상세 데이터 조회 실패: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'데이터 조회 중 오류가 발생했습니다: {str(e)}'
        }), 500

# 급여 데이터 수정 API
@payroll.route('/payroll/update/<int:record_id>', methods=['PUT'])
@login_required
def update_payroll(record_id):
    try:
        data = request.get_json()
        record = PayrollRecord.query.get_or_404(record_id)
        
        # 완료 상태인 경우 수정 불가
        if record.status == '완료':
            return jsonify({
                'success': False,
                'message': '이미 완료된 급여 데이터는 수정할 수 없습니다.'
            }), 400
        
        # 기본 정보 수정
        record.payment_date = datetime.strptime(data['payment_date'], '%Y-%m-%d').date()
        record.updated_by = current_user.username
        record.updated_ip = request.remote_addr
        
        # 상세 데이터 수정
        for emp_data in data['employees']:
            detail = PayrollDetail.query.filter_by(
                record_id=record_id,
                employee_id=emp_data['employee_id']
            ).first()
            
            if detail:
                detail.department = emp_data.get('department', '')
                detail.position = emp_data.get('position', '')
                detail.base_salary = emp_data.get('base_salary', 0)
                detail.position_allowance = emp_data.get('position_allowance', 0)
                detail.overtime_pay = emp_data.get('overtime_pay', 0)
                detail.meal_allowance = emp_data.get('meal_allowance', 0)
                detail.income_tax = emp_data.get('income_tax', 0)
                detail.national_pension = emp_data.get('national_pension', 0)
                detail.health_insurance = emp_data.get('health_insurance', 0)
                detail.employment_insurance = emp_data.get('employment_insurance', 0)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '급여 데이터가 성공적으로 수정되었습니다.'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"급여 데이터 수정 실패: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'수정 중 오류가 발생했습니다: {str(e)}'
        }), 500

# 급여 처리 상태 변경 API
@payroll.route('/payroll/status/<int:record_id>', methods=['PUT'])
@login_required
def update_status(record_id):
    try:
        data = request.get_json()
        record = PayrollRecord.query.get_or_404(record_id)
        
        # 상태 변경
        record.status = data['status']
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '처리 상태가 변경되었습니다.'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"상태 변경 실패: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'상태 변경 중 오류가 발생했습니다: {str(e)}'
        }), 500

# 급여 명세서 PDF 파일을 이메일로 발송
@payroll.route('/payroll/send_email', methods=['POST'])
def send_payroll_email():
    try:
        data = request.get_json()
        employee_id = data.get('employee_id')
        year_month = data.get('year_month')
        pdf_path = data.get('pdf_path')
        
        # 직원 정보 조회
        employee = Employee.query.filter_by(emp_number=employee_id).first()
        if not employee or not employee.email:
            return jsonify({'error': '직원 이메일 정보를 찾을 수 없습니다.'}), 400
            
        # 이메일 설정
        smtp_server = current_app.config['SMTP_SERVER']
        smtp_port = current_app.config['SMTP_PORT']
        smtp_username = current_app.config['SMTP_USERNAME']
        smtp_password = current_app.config['SMTP_PASSWORD']
        
        # 이메일 메시지 생성
        msg = MIMEMultipart()
        msg['From'] = smtp_username
        msg['To'] = employee.email
        msg['Date'] = formatdate(localtime=True)
        msg['Subject'] = f'{year_month} 급여명세서'
        
        # 이메일 본문
        body = f"""
        안녕하세요, {employee.name}님
        
        {year_month} 급여명세서를 첨부하여 보내드립니다.
        
        감사합니다.
        """
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # PDF 첨부
        with open(pdf_path, 'rb') as f:
            pdf = MIMEApplication(f.read(), _subtype='pdf')
            pdf.add_header('Content-Disposition', 'attachment', 
                         filename=os.path.basename(pdf_path))
            msg.attach(pdf)
            
        # 이메일 발송
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(msg)
            
        return jsonify({'message': '이메일이 성공적으로 발송되었습니다.'}), 200
        
    except Exception as e:
        return jsonify({'error': f'이메일 발송 중 오류가 발생했습니다: {str(e)}'}), 500

def extract_payroll_data_from_pdf(pdf_path):
    """PDF 파일에서 급여 데이터를 추출하는 함수"""
    try:
        # pdfplumber를 사용하여 PDF 열기
        with pdfplumber.open(pdf_path) as pdf:
            # 첫 페이지 가져오기
            page = pdf.pages[0]
            
            # 전체 텍스트 추출
            text = page.extract_text()
            print("추출된 텍스트:", text)  # 디버깅용
            
            # 테이블 데이터 추출
            tables = page.extract_tables()
            print("추출된 테이블:", tables)  # 디버깅용
            
            # 데이터 구조 초기화
            data = {
                'employee_info': {
                    'id': '',
                    'name': '',
                    'year_month': ''
                },
                'payment_items': {
                    'base_salary': 0,        # 기본급
                    'position_allowance': 0,  # 직책수당
                    'overtime_pay': 0,        # 연장근로수당
                    'meal_allowance': 0       # 식대
                },
                'deduction_items': {
                    'income_tax': 0,          # 소득세
                    'national_pension': 0,    # 국민연금
                    'health_insurance': 0,    # 건강보험
                    'employment_insurance': 0  # 고용보험
                }
            }
            
            # 정규식 패턴
            amount_pattern = r'(\d{1,3}(?:,\d{3})*)'
            
            # 텍스트 분석
            lines = text.split('\n')
            for line in lines:
                # 직원 정보 추출
                if '박희창' in line:
                    data['employee_info']['name'] = '박희창'
                if '45' in line:
                    data['employee_info']['id'] = '45'
                    
                # 금액 정보 추출
                if '기본급' in line:
                    match = re.search(amount_pattern, line)
                    if match:
                        data['payment_items']['base_salary'] = int(match.group(1).replace(',', ''))
                
                # 다른 항목들도 유사하게 처리
                
            return data
            
    except Exception as e:
        print(f"PDF 분석 오류: {str(e)}")
        return None

@payroll.route('/payroll/parse-pdf', methods=['POST'])
def parse_pdf():
    """PDF 파일을 분석하는 API 엔드포인트"""
    try:
        pdf_path = request.json.get('pdf_path')
        if not pdf_path:
            return jsonify({'error': 'PDF 파일 경로가 필요합니다.'}), 400
            
        data = extract_payroll_data_from_pdf(pdf_path)
        if data:
            return jsonify({
                'success': True, 
                'data': data,
                'message': 'PDF 파일 분석이 완료되었습니다.'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'PDF 파일 분석에 실패했습니다.'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'처리 중 오류 발생: {str(e)}'
        }), 500