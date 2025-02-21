from functools import wraps
from flask import jsonify, flash, redirect, url_for, request
from flask_login import current_user

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            # API 요청인 경우 JSON 응답
            if request.is_json or request.accept_mimetypes.best == 'application/json':
                return jsonify({
                    'success': False,
                    'message': '관리자 권한이 필요합니다.'
                }), 403
            # 웹 페이지 요청인 경우 오류 메시지와 함께 리다이렉트
            flash('이 페이지에 접근하려면 관리자 권한이 필요합니다.', 'danger')
            return redirect(url_for('payroll.index'))
        return f(*args, **kwargs)
    return decorated_function 