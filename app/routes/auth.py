from flask import Blueprint, render_template, redirect, url_for, flash, request, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app.models import User
from app.forms import LoginForm
from app import db
from datetime import datetime
from functools import wraps

auth = Blueprint('auth', __name__)

def check_login_attempts(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('login_attempts', 0) >= current_app.config['MAX_LOGIN_ATTEMPTS']:
            if 'login_blocked_until' not in session:
                session['login_blocked_until'] = datetime.now().timestamp() + 1800  # 30분 블록
            elif datetime.now().timestamp() < session['login_blocked_until']:
                flash('너무 많은 로그인 시도로 인해 계정이 일시적으로 잠겼습니다. 30분 후에 다시 시도해주세요.', 'danger')
                return redirect(url_for('auth.login'))
            else:
                session.pop('login_attempts', None)
                session.pop('login_blocked_until', None)
        return f(*args, **kwargs)
    return decorated_function

@auth.route('/', methods=['GET', 'POST'])
@auth.route('/login', methods=['GET', 'POST'])
@check_login_attempts
def login():
    if current_user.is_authenticated:
        return redirect(url_for('auth.dashboard'))
        
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            # 로그인 상태 유지 설정
            if form.remember.data:
                # 30일 동안 로그인 유지
                session.permanent = True
                login_user(user, remember=True, 
                         duration=current_app.config['REMEMBER_COOKIE_DURATION'])
            else:
                # 브라우저 종료시까지만 유지
                session.permanent = False
                login_user(user, remember=False)
            
            session.pop('login_attempts', None)
            
            # 로그인 성공 로그 기록
            user.last_login = datetime.now()
            user.login_ip = request.remote_addr
            user.failed_login_attempts = 0  # 로그인 실패 횟수 초기화
            db.session.commit()
            
            # 원래 요청한 페이지로 리다이렉트
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('auth.dashboard')
            return redirect(next_page)
            
        # 로그인 실패 처리
        session['login_attempts'] = session.get('login_attempts', 0) + 1
        remaining_attempts = current_app.config['MAX_LOGIN_ATTEMPTS'] - session['login_attempts']
        flash(f'아이디 또는 비밀번호가 올바르지 않습니다. (남은 시도 횟수: {remaining_attempts}회)', 'danger')
        
    return render_template('auth/login.html', form=form)

@auth.route('/dashboard')
@login_required
def dashboard():
    return render_template('auth/dashboard.html')

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()  # 세션 완전 삭제
    flash('로그아웃되었습니다.', 'info')
    return redirect(url_for('auth.login')) 