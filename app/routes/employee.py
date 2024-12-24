from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, current_app, send_file
from flask_login import login_required, current_user
from app import db
from app.models import Employee, User, EmployeeHistory
from datetime import datetime
from functools import wraps
import re
import pandas as pd
import os
from sqlalchemy import or_, and_
import tempfile
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

employee = Blueprint('employee', __name__)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            return jsonify({
                'success': False,
                'message': '관리자 권한이 필요합니다.'
            }), 403
        return f(*args, **kwargs)
    return decorated_function

def validate_employee_data(data, is_update=False):
    errors = []
    
    # 필수 필드 검증
    if not is_update:
        if not data.get('emp_number'):
            errors.append('사번은 필수 입력 항목입니다.')
        if not data.get('name'):
            errors.append('성명은 필수 입력 항목입니다.')
            
    # 사번 형식 검증
    if data.get('emp_number') and not re.match(r'^[A-Za-z0-9]{4,10}$', data['emp_number']):
        errors.append('사번은 4-10자리의 영문자와 숫자만 가능합니다.')
        
    # 이메일 형식 검증
    if data.get('email') and not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', data['email']):
        errors.append('올바른 이메일 형식이 아닙니다.')
        
    # 날짜 형식 검증
    for date_field in ['birth_date', 'join_date']:
        if data.get(date_field):
            try:
                datetime.strptime(data[date_field], '%Y-%m-%d')
            except ValueError:
                errors.append(f'{date_field}의 형식이 올바르지 않습니다. (YYYY-MM-DD)')
    
    return errors

@employee.route('/employee')
@login_required
@admin_required
def index():
    return render_template('employee/employee.html')

@employee.route('/employee/list', methods=['GET'])
@login_required
@admin_required
def get_employee_list():
    try:
        logger.info("직원 목록 조회 시작")
        employees = Employee.query.all()
        logger.info(f"조회된 직원 수: {len(employees)}")
        
        result = []
        for emp in employees:
            try:
                result.append({
                    'id': emp.id,
                    'emp_number': emp.emp_number,
                    'name': emp.name,
                    'birth_date': emp.birth_date.strftime('%Y-%m-%d') if emp.birth_date else '',
                    'join_date': emp.join_date.strftime('%Y-%m-%d') if emp.join_date else '',
                    'position': emp.position,
                    'email': emp.email,
                    'created_at': emp.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    'created_by': emp.created_by,
                    'updated_at': emp.updated_at.strftime('%Y-%m-%d %H:%M:%S') if emp.updated_at else '',
                    'updated_by': emp.updated_by
                })
            except Exception as e:
                logger.error(f"직원 데이터 변환 중 오류 발생: {str(e)}, 직원 ID: {emp.id}")
                continue
        
        logger.info("직원 목록 조회 완료")
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        logger.error(f"직원 목록 조회 중 오류 발생: {str(e)}")
        return jsonify({'success': True, 'data': []})

@employee.route('/employee/save', methods=['POST'])
@login_required
@admin_required
def save_employee():
    try:
        data = request.get_json()
        
        # 데이터 유효성 검사
        errors = validate_employee_data(data)
        if errors:
            return jsonify({
                'success': False,
                'message': '입력 데이터가 올바르지 않습니다.',
                'errors': errors
            }), 400
            
        # 사번 중복 체크
        existing_emp = Employee.query.filter_by(emp_number=data['emp_number']).first()
        if existing_emp:
            return jsonify({
                'success': False,
                'message': f"사번 '{data['emp_number']}'가 이미 존재합니다."
            }), 409
            
        # 새 직원 생성
        employee = Employee(
            emp_number=data['emp_number'],
            name=data['name'],
            birth_date=datetime.strptime(data['birth_date'], '%Y-%m-%d').date() if data.get('birth_date') else None,
            join_date=datetime.strptime(data['join_date'], '%Y-%m-%d').date() if data.get('join_date') else None,
            position=data.get('position', ''),
            email=data.get('email', ''),
            created_by=current_user.username,
            created_ip=request.remote_addr
        )
        
        db.session.add(employee)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '직원이 성공적으로 등록되었습니다.'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'직원 등록 중 오류가 발생했습니다: {str(e)}'
        }), 500

@employee.route('/employee/update/<int:id>', methods=['PUT'])
@login_required
@admin_required
def update_employee(id):
    try:
        employee = Employee.query.get_or_404(id)
        data = request.get_json()
        
        # 데이터 유효성 검사
        errors = validate_employee_data(data, is_update=True)
        if errors:
            return jsonify({
                'success': False,
                'message': '입력 데이터가 올바르지 않습니다.',
                'errors': errors
            }), 400
        
        # 사번 변경 시 중복 체크
        if data.get('emp_number') and data['emp_number'] != employee.emp_number:
            existing_emp = Employee.query.filter_by(emp_number=data['emp_number']).first()
            if existing_emp:
                return jsonify({
                    'success': False,
                    'message': f"사번 '{data['emp_number']}'가 이미 존재합니다."
                }), 409
        
        # 변경 이력 기록
        field_mappings = {
            'emp_number': '사번',
            'name': '성명',
            'birth_date': '생년월일',
            'join_date': '입사일',
            'position': '직위',
            'email': '이메일'
        }
        
        # 데이터 업데이트 및 이력 기록
        for field, value in data.items():
            if hasattr(employee, field) and getattr(employee, field) != value:
                old_value = getattr(employee, field)
                if isinstance(old_value, datetime.date):
                    old_value = old_value.strftime('%Y-%m-%d')
                
                # 날짜 필드 처리
                if field in ['birth_date', 'join_date'] and value:
                    value = datetime.strptime(value, '%Y-%m-%d').date()
                
                # 이력 기록
                employee.record_history(
                    field_name=field_mappings.get(field, field),
                    old_value=old_value,
                    new_value=value,
                    user=current_user.username,
                    ip_address=request.remote_addr
                )
                
                # 값 업데이트
                setattr(employee, field, value)
        
        # 수정 정보 기록
        employee.updated_by = current_user.username
        employee.updated_ip = request.remote_addr
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '직원 정보가 성공적으로 수정되었습니다.'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'직원 정보 수정 중 오류가 발생했습니다: {str(e)}'
        }), 500

@employee.route('/employee/delete/<int:id>', methods=['DELETE'])
@login_required
@admin_required
def delete_employee(id):
    try:
        employee = Employee.query.get_or_404(id)
        
        # 급여 데이터가 있는지 확인
        if employee.salaries:
            return jsonify({
                'success': False,
                'message': '급여 정보가 있는 직원은 삭제할 수 없습니다.'
            }), 400
        
        db.session.delete(employee)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '직원이 성공적으로 삭제되었습니다.'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'직원 삭제 중 오류가 발생했습니다: {str(e)}'
        }), 500

# 직원 일괄 등록
@employee.route('/employee/bulk-save', methods=['POST'])
@login_required
@admin_required
def bulk_save_employees():
    try:
        data = request.get_json()
        if not data or not isinstance(data, list):
            return jsonify({
                'success': False,
                'message': '올바른 데이터 형식이 아닙니다.'
            }), 400
            
        success_count = 0
        errors = []
        
        for idx, emp_data in enumerate(data):
            # 데이터 유효성 검사
            validation_errors = validate_employee_data(emp_data)
            if validation_errors:
                errors.append({
                    'index': idx,
                    'emp_number': emp_data.get('emp_number'),
                    'errors': validation_errors
                })
                continue
                
            # 사번 중복 체크
            if Employee.query.filter_by(emp_number=emp_data['emp_number']).first():
                errors.append({
                    'index': idx,
                    'emp_number': emp_data['emp_number'],
                    'errors': ['이미 존재하는 사번입니다.']
                })
                continue
                
            # 직원 생성
            employee = Employee(
                emp_number=emp_data['emp_number'],
                name=emp_data['name'],
                birth_date=datetime.strptime(emp_data['birth_date'], '%Y-%m-%d').date() if emp_data.get('birth_date') else None,
                join_date=datetime.strptime(emp_data['join_date'], '%Y-%m-%d').date() if emp_data.get('join_date') else None,
                position=emp_data.get('position', ''),
                email=emp_data.get('email', ''),
                created_by=current_user.username,
                created_ip=request.remote_addr
            )
            db.session.add(employee)
            success_count += 1
            
        if success_count > 0:
            db.session.commit()
            
        return jsonify({
            'success': True,
            'message': f'{success_count}명의 직원이 등록되었습니다.',
            'errors': errors if errors else None
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'직원 일괄 등록 중 오류가 발생했습니다: {str(e)}'
        }), 500

# 직원 검�� 및 필터링
@employee.route('/employee/search', methods=['GET'])
@login_required
@admin_required
def search_employees():
    try:
        # 검색 파라미터
        query = request.args.get('query', '')
        position = request.args.get('position', '')
        start_date = request.args.get('start_date', '')
        end_date = request.args.get('end_date', '')
        sort_by = request.args.get('sort_by', 'emp_number')
        order = request.args.get('order', 'asc')
        
        # 기본 쿼리
        employees = Employee.query
        
        # 검색어 적용
        if query:
            employees = employees.filter(
                or_(
                    Employee.emp_number.ilike(f'%{query}%'),
                    Employee.name.ilike(f'%{query}%'),
                    Employee.email.ilike(f'%{query}%')
                )
            )
        
        # 직위 필터
        if position:
            employees = employees.filter(Employee.position == position)
            
        # 입사일 범위 필터
        if start_date and end_date:
            employees = employees.filter(
                and_(
                    Employee.join_date >= datetime.strptime(start_date, '%Y-%m-%d').date(),
                    Employee.join_date <= datetime.strptime(end_date, '%Y-%m-%d').date()
                )
            )
        
        # 정렬
        if hasattr(Employee, sort_by):
            if order == 'desc':
                employees = employees.order_by(getattr(Employee, sort_by).desc())
            else:
                employees = employees.order_by(getattr(Employee, sort_by))
        
        result = [emp.to_dict() for emp in employees.all()]
        
        return jsonify({
            'success': True,
            'data': result,
            'total': len(result)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'직원 검색 중 오류가 발생했습니다: {str(e)}'
        }), 500

# 직원 정보 엑셀 다운로드
@employee.route('/employee/export', methods=['GET'])
@login_required
@admin_required
def export_employees():
    try:
        employees = Employee.query.all()
        data = []
        
        for emp in employees:
            data.append({
                '사번': emp.emp_number,
                '성명': emp.name,
                '생년월일': emp.birth_date.strftime('%Y-%m-%d') if emp.birth_date else '',
                '입사일': emp.join_date.strftime('%Y-%m-%d') if emp.join_date else '',
                '직위': emp.position,
                '이메일': emp.email,
                '등록일': emp.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                '등록자': emp.created_by,
                '수정일': emp.updated_at.strftime('%Y-%m-%d %H:%M:%S') if emp.updated_at else '',
                '수정자': emp.updated_by
            })
        
        df = pd.DataFrame(data)
        
        # 엑셀 파일 생성
        filename = f'직원명부_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        excel_path = os.path.join(current_app.root_path, 'static', 'temp', filename)
        os.makedirs(os.path.dirname(excel_path), exist_ok=True)
        
        # 엑셀 스타일 지정
        writer = pd.ExcelWriter(excel_path, engine='xlsxwriter')
        df.to_excel(writer, index=False, sheet_name='직원명부')
        
        # 열 너비 자동 조정
        worksheet = writer.sheets['직원명부']
        for idx, col in enumerate(df.columns):
            max_length = max(df[col].astype(str).apply(len).max(), len(col)) + 2
            worksheet.set_column(idx, idx, max_length)
            
        writer.close()
        
        return send_file(excel_path, as_attachment=True, download_name=filename)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'엑셀 파일 생성 중 오류가 발생했습니다: {str(e)}'
        }), 500

# 직원 ���보 엑셀 일괄 등록
@employee.route('/employee/import', methods=['POST'])
@login_required
@admin_required
def import_employees():
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'message': '파일이 전송되지 않았습니다.'
            }), 400
            
        file = request.files['file']
        if not file.filename.endswith('.xlsx'):
            return jsonify({
                'success': False,
                'message': 'Excel 파일(.xlsx)만 업로드 가능합니다.'
            }), 400
            
        # 엑셀 파일 읽기
        df = pd.read_excel(file)
        required_columns = ['사번', '성명', '생년월일', '입사일', '직위', '이메일']
        
        # 필수 컬럼 확인
        if not all(col in df.columns for col in required_columns):
            return jsonify({
                'success': False,
                'message': f'필수 컬럼이 누락되었습니다. (필수: {", ".join(required_columns)})'
            }), 400
            
        success_count = 0
        errors = []
        
        for idx, row in df.iterrows():
            try:
                emp_data = {
                    'emp_number': str(row['사번']),
                    'name': row['성명'],
                    'birth_date': row['생년월일'].strftime('%Y-%m-%d') if pd.notna(row['생년월일']) else None,
                    'join_date': row['입사일'].strftime('%Y-%m-%d') if pd.notna(row['입사일']) else None,
                    'position': row['직위'] if pd.notna(row['직위']) else '',
                    'email': row['이메일'] if pd.notna(row['이메일']) else ''
                }
                
                # 데이터 유효성 검사
                validation_errors = validate_employee_data(emp_data)
                if validation_errors:
                    errors.append({
                        'row': idx + 2,  # Excel 행 번호 (헤더 제외)
                        'emp_number': emp_data['emp_number'],
                        'errors': validation_errors
                    })
                    continue
                    
                # 사번 중복 체크
                if Employee.query.filter_by(emp_number=emp_data['emp_number']).first():
                    errors.append({
                        'row': idx + 2,
                        'emp_number': emp_data['emp_number'],
                        'errors': ['이미 존재하는 사번입니다.']
                    })
                    continue
                    
                # 직원 생성
                employee = Employee(
                    emp_number=emp_data['emp_number'],
                    name=emp_data['name'],
                    birth_date=datetime.strptime(emp_data['birth_date'], '%Y-%m-%d').date() if emp_data['birth_date'] else None,
                    join_date=datetime.strptime(emp_data['join_date'], '%Y-%m-%d').date() if emp_data['join_date'] else None,
                    position=emp_data['position'],
                    email=emp_data['email'],
                    created_by=current_user.username,
                    created_ip=request.remote_addr
                )
                db.session.add(employee)
                success_count += 1
                
            except Exception as e:
                errors.append({
                    'row': idx + 2,
                    'emp_number': str(row['사번']),
                    'errors': [str(e)]
                })
                
        if success_count > 0:
            db.session.commit()
            
        return jsonify({
            'success': True,
            'message': f'{success_count}명의 직원이 등록되었습니다.',
            'errors': errors if errors else None
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'엑셀 파일 처리 중 오류가 발생했습니다: {str(e)}'
        }), 500

# 직원 변경 이력 조회
@employee.route('/employee/history/<int:id>', methods=['GET'])
@login_required
@admin_required
def get_employee_history(id):
    try:
        employee = Employee.query.get_or_404(id)
        histories = EmployeeHistory.query.filter_by(employee_id=id).order_by(EmployeeHistory.changed_at.desc()).all()
        
        result = []
        for history in histories:
            result.append({
                'field_name': history.field_name,
                'old_value': history.old_value,
                'new_value': history.new_value,
                'changed_by': history.changed_by,
                'changed_at': history.changed_at.strftime('%Y-%m-%d %H:%M:%S'),
                'changed_ip': history.changed_ip
            })
            
        return jsonify({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'변경 이력 조회 중 오류가 발생했습니다: {str(e)}'
        }), 500

# 직원 통계
@employee.route('/employee/stats', methods=['GET'])
@login_required
@admin_required
def get_employee_stats():
    try:
        # 전체 직원 수
        total_count = Employee.query.count()
        
        # 직위별 직원 수
        position_stats = db.session.query(
            Employee.position,
            db.func.count(Employee.id)
        ).group_by(Employee.position).all()
        
        # 입사년도별 직원 수
        join_year_stats = db.session.query(
            db.func.strftime('%Y', Employee.join_date),
            db.func.count(Employee.id)
        ).group_by(db.func.strftime('%Y', Employee.join_date)).all()
        
        return jsonify({
            'success': True,
            'data': {
                'total_count': total_count,
                'position_stats': dict(position_stats),
                'join_year_stats': dict(join_year_stats)
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'통계 데이터 조회 중 오류가 발생했습니다: {str(e)}'
        }), 500 