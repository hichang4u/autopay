from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, current_app, send_file
from flask_login import login_required, current_user
from app import db
from app.models import PayrollRecord, PayrollDetail, Employee, User
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
import pdfkit
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

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
            status='TEMP_SAVE',
            created_by=current_user.username,
            created_ip=request.remote_addr
        )
        db.session.add(record)
        db.session.flush()
        
        # PayrollDetail 생성
        for emp_data in data['employees']:
            # 지급액 계산
            total_payment = (
                int(emp_data.get('base_salary', 0)) +
                int(emp_data.get('position_allowance', 0)) +
                int(emp_data.get('meal_allowance', 0)) +
                int(emp_data.get('car_allowance', 0))
            )
            
            # 공제액 계산
            total_deduction = (
                int(emp_data.get('income_tax', 0)) +
                int(emp_data.get('local_income_tax', 0)) +
                int(emp_data.get('national_pension', 0)) +
                int(emp_data.get('health_insurance', 0)) +
                int(emp_data.get('long_term_care', 0)) +
                int(emp_data.get('employment_insurance', 0))
            )
            
            detail = PayrollDetail(
                record_id=record.id,
                employee_id=emp_data['employee_id'],
                employee_name=emp_data['employee_name'],
                department=emp_data.get('department', ''),
                position=emp_data.get('position', ''),
                
                # 지급 항목
                base_salary=int(emp_data.get('base_salary', 0)),
                position_allowance=int(emp_data.get('position_allowance', 0)),
                meal_allowance=int(emp_data.get('meal_allowance', 0)),
                car_allowance=int(emp_data.get('car_allowance', 0)),
                total_payment=total_payment,
                
                # 공제 항목
                income_tax=int(emp_data.get('income_tax', 0)),
                local_income_tax=int(emp_data.get('local_income_tax', 0)),
                national_pension=int(emp_data.get('national_pension', 0)),
                health_insurance=int(emp_data.get('health_insurance', 0)),
                long_term_care=int(emp_data.get('long_term_care', 0)),
                employment_insurance=int(emp_data.get('employment_insurance', 0)),
                total_deduction=total_deduction
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
        record_id = data.get('record_id')
        employee_id = data.get('employee_id')
        
        if not record_id or not employee_id:
            return jsonify({
                'success': False,
                'message': '필수 파라미터가 누락되었습니다.'
            }), 400
            
        # 급여 기록 조회
        record = PayrollRecord.query.get_or_404(record_id)
        detail = PayrollDetail.query.filter_by(record_id=record_id, employee_id=employee_id).first()
        
        if not detail:
            return jsonify({
                'success': False,
                'message': '해당 직원의 급여 데이터를 찾을 수 없습니다.'
            }), 404
            
        # 직원 정보 조회
        employee = Employee.query.filter_by(employee_id=employee_id).first()
        if not employee or not employee.email:
            return jsonify({
                'success': False,
                'message': '직원의 이메일 정보가 없습니다.'
            }), 400
            
        # 담당자 정보 가져오기
        created_by_user = User.query.filter_by(username=record.created_by).first()
        if not created_by_user or not created_by_user.email:
            return jsonify({
                'success': False,
                'message': '담당자의 이메일 정보가 없습니다.'
            }), 400
            
        # PDF 파일 경로
        payment_date = record.payment_date.strftime('%Y%m%d')
        pdf_filename = f"{detail.employee_id}_{detail.employee_name}_{record.pay_year_month}({payment_date}).pdf"
        pdf_dir = os.path.join(current_app.static_folder, 'pdfs', payment_date)
        pdf_path = os.path.join(pdf_dir, pdf_filename)
        
        if not os.path.exists(pdf_path):
            return jsonify({
                'success': False,
                'message': '급여명세서 PDF 파일이 없습니다.'
            }), 404
            
        # 이메일 메시지 생성
        msg = MIMEMultipart()
        msg['From'] = created_by_user.email  # 담당자 이메일로 변경
        msg['To'] = employee.email
        msg['Date'] = formatdate(localtime=True)
        msg['Subject'] = f"{record.pay_year_month} 급여명세서"
        
        # 이메일 본문
        body = f"""
안녕하세요, {detail.employee_name}님

{record.pay_year_month} 귀속 급여명세서를 첨부하여 보내드립니다.
감사합니다.

{created_by_user.name}
{created_by_user.phone}
(주)우리소프트
        """
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # PDF 첨부
        with open(pdf_path, 'rb') as f:
            pdf = MIMEApplication(f.read(), _subtype='pdf')
            pdf.add_header('Content-Disposition', 'attachment', filename=pdf_filename)
            msg.attach(pdf)
            
        # 이메일 발송
        with smtplib.SMTP(current_app.config['MAIL_SERVER'], current_app.config['MAIL_PORT']) as server:
            server.starttls()
            server.login(current_app.config['MAIL_USERNAME'], current_app.config['MAIL_PASSWORD'])
            server.send_message(msg)
            
        return jsonify({
            'success': True,
            'message': '이메일이 성공적으로 발송되었습니다.'
        })
        
    except Exception as e:
        logger.error(f"이메일 발송 실패: {str(e)}")
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
        
        # NaN 값 처리
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
@payroll.route('/payroll/list')
@login_required
def get_payroll_list():
    """급여 목록 조회"""
    try:
        records = PayrollRecord.query.order_by(desc(PayrollRecord.pay_year_month)).all()
        return jsonify({
            'success': True,
            'data': [{
                'id': record.id,
                'pay_year_month': record.pay_year_month,
                'payment_date': record.payment_date.strftime('%Y-%m-%d'),
                'status': record.status,
                'employee_count': PayrollDetail.query.filter_by(record_id=record.id).count(),
                'created_at': record.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'created_by': record.created_by,
                'updated_at': record.updated_at.strftime('%Y-%m-%d %H:%M:%S') if record.updated_at else None,
                'updated_by': record.updated_by
            } for record in records]
        })
    except Exception as e:
        logger.error(f"급여 데이터 조회 실패: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'데이터 조회 중 오류가 발생했습니다: {str(e)}'
        }), 500

# 급여 상세 데이터 조회 API
@payroll.route('/payroll/detail/<int:record_id>')
@login_required
def get_payroll_detail(record_id):
    """급여 상세 조회"""
    try:
        record = PayrollRecord.query.get_or_404(record_id)
        details = PayrollDetail.query.filter_by(record_id=record_id).all()
        
        detail_list = [{
            'employee_id': detail.employee_id,
            'employee_name': detail.employee_name,
            'department': detail.department,
            'position': detail.position,
            'base_salary': detail.base_salary,
            'position_allowance': detail.position_allowance,
            'meal_allowance': detail.meal_allowance,
            'car_allowance': detail.car_allowance,
            'income_tax': detail.income_tax,
            'local_income_tax': detail.local_income_tax,
            'national_pension': detail.national_pension,
            'health_insurance': detail.health_insurance,
            'long_term_care': detail.long_term_care,
            'employment_insurance': detail.employment_insurance,
            'total_payment': detail.total_payment,
            'total_deduction': detail.total_deduction
        } for detail in details]
        
        return jsonify({
            'success': True,
            'data': {
                'id': record.id,
                'pay_year_month': record.pay_year_month,
                'payment_date': record.payment_date.strftime('%Y-%m-%d'),
                'status': record.status,
                'details': detail_list
            }
        })
    except Exception as e:
        logger.error(f"급여 상세 조회 실패: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'상세 정보 조회 중 오류가 발생했습니다: {str(e)}'
        }), 500

# 급여 데이터 수정 API
@payroll.route('/payroll/update/<int:record_id>', methods=['PUT'])
@login_required
def update_payroll(record_id):
    try:
        data = request.get_json()
        record = PayrollRecord.query.get_or_404(record_id)
        
        # 완료 상태인 경우 수정 불가
        if record.status == 'PROC_CMPT':
            return jsonify({
                'success': False,
                'message': '이미 완료된 급여 데이터는 수정할 수 없습니다.'
            }), 400
        
        # 기본 정보 수정
        if data.get('payment_date'):
            try:
                record.payment_date = datetime.strptime(data['payment_date'], '%Y-%m-%d').date()
            except ValueError:
                return jsonify({
                    'success': False,
                    'message': '지급일 형식이 올바르지 않습니다. (YYYY-MM-DD)'
                }), 400
                
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
                detail.base_salary = int(emp_data.get('base_salary', 0))
                detail.position_allowance = int(emp_data.get('position_allowance', 0))
                detail.meal_allowance = int(emp_data.get('meal_allowance', 0))
                detail.car_allowance = int(emp_data.get('car_allowance', 0))
                detail.income_tax = int(emp_data.get('income_tax', 0))
                detail.local_income_tax = int(emp_data.get('local_income_tax', 0))
                detail.national_pension = int(emp_data.get('national_pension', 0))
                detail.health_insurance = int(emp_data.get('health_insurance', 0))
                detail.long_term_care = int(emp_data.get('long_term_care', 0))
                detail.employment_insurance = int(emp_data.get('employment_insurance', 0))
                
                # 지급액 계산
                total_payment = (
                    detail.base_salary +
                    detail.position_allowance +
                    detail.meal_allowance +
                    detail.car_allowance
                )
                
                # 공제액 계산
                total_deduction = (
                    detail.income_tax +
                    detail.local_income_tax +
                    detail.national_pension +
                    detail.health_insurance +
                    detail.long_term_care +
                    detail.employment_insurance
                )
                
                detail.total_payment = total_payment
                detail.total_deduction = total_deduction
        
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

@payroll.route('/payroll/delete/<int:record_id>', methods=['DELETE'])
@login_required
def delete_payroll(record_id):
    try:
        # 급여 기록 조회
        payroll = PayrollRecord.query.get_or_404(record_id)
        
        # 임시저장 상태인 경우에만 삭제 가능
        if payroll.status != 'TEMP_SAVE':
            return jsonify({
                'success': False,
                'message': '임시저장 상태의 급여 데이터만 삭제할 수 있습니다.'
            }), 400
        
        # 관련된 상세 기록도 함께 삭제
        PayrollDetail.query.filter_by(record_id=record_id).delete()
        
        # 급여 기록 삭제
        db.session.delete(payroll)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '급여 데이터가 삭제되었습니다.'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'삭제 중 오류가 발생했습니다: {str(e)}'
        }), 500

@payroll.route('/generate-pdf/<int:record_id>', methods=['POST'])
def generate_pdf(record_id):
    try:
        # 급여 기록 조회
        record = PayrollRecord.query.get_or_404(record_id)
        details = PayrollDetail.query.filter_by(record_id=record_id).all()
        
        if not details:
            return jsonify({'success': False, 'message': '급여 상세 데이터가 없습니다.'})
            
        # PDF 저장 디렉토리 생성 (지급일 기준)
        payment_date = record.payment_date.strftime('%Y%m%d')
        pdfs_dir = os.path.join(current_app.static_folder, 'pdfs')
        os.makedirs(pdfs_dir, exist_ok=True)  # pdfs 디렉토리 생성

        pdf_dir = os.path.join(pdfs_dir, payment_date)
        os.makedirs(pdf_dir, exist_ok=True)  # 지급일 기준 디렉토리 생성

        logger.info(f"PDF 저장 디렉토리 생성: {pdf_dir}")  # 로그 추가

        generated_count = 0
        
        # 각 직원별로 PDF 생성
        for detail in details:
            # PDF 파일명 생성 (사번_이름_귀속년월(지급일))
            pdf_filename = f"{detail.employee_id}_{detail.employee_name}_{record.pay_year_month}({payment_date}).pdf"
            pdf_path = os.path.join(pdf_dir, pdf_filename)
            
            # 담당자 정보 가져오기
            created_by_user = User.query.filter_by(username=record.created_by).first()
            if not created_by_user:
                created_by_name = record.created_by
                created_by_phone = '-'
                created_by_email = '-'
            else:
                created_by_name = created_by_user.name if created_by_user.name else created_by_user.username
                created_by_phone = created_by_user.phone if created_by_user.phone else '-'
                created_by_email = created_by_user.email if created_by_user.email else '-'
            
            logger.info(f"담당자 정보: {created_by_name}, {created_by_phone}, {created_by_email}")  # 로그 추가
            
            # HTML 템플릿 렌더링
            html = render_template('payroll/payroll_pdf.html',
                                record=record,
                                detail=detail,
                                created_by_name=created_by_name,
                                created_by_phone=created_by_phone,
                                created_by_email=created_by_email)
            
            # 임시 HTML 파일 생성 (현재 작업 디렉토리에)
            temp_html = f'temp_{detail.employee_id}.html'
            with open(temp_html, 'w', encoding='utf-8') as f:
                f.write(html)
            
            # PDF 생성 옵션 설정
            options = {
                'enable-local-file-access': None,
                'encoding': 'utf-8',
                'page-size': 'A4',
                'margin-top': '0.75in',
                'margin-right': '0.75in',
                'margin-bottom': '0.75in',
                'margin-left': '0.75in'
            }
            
            try:
                # PDF 생성
                config = pdfkit.configuration(wkhtmltopdf=r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe')
                pdfkit.from_file(temp_html, pdf_path, options=options, configuration=config)
                generated_count += 1
                logger.info(f"PDF 생성 성공: {pdf_filename}")
                
            except Exception as e:
                logger.error(f"PDF 생성 중 오류 발생: {str(e)}")
                raise
            finally:
                # 임시 HTML 파일 삭제
                if os.path.exists(temp_html):
                    os.remove(temp_html)
        
        # 상태 업데이트
        record.status = 'PDF_GEN'
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'{generated_count}개의 PDF 파일이 생성되었습니다.',
            'data': {
                'count': generated_count,
                'directory': pdf_dir
            }
        })
        
    except Exception as e:
        logger.error(f"PDF 생성 실패: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'PDF 생성 중 오류가 발생했습니다: {str(e)}'
        }), 500