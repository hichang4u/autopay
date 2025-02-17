from flask import Blueprint, render_template, redirect, url_for, flash, request, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app.models import User
from app.forms import LoginForm, PasswordResetRequestForm
from app import db
from datetime import datetime
from functools import wraps
import random
import string
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

auth = Blueprint('auth', __name__)

def check_login_attempts(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 이미 로그인한 사용자는 체크하지 않음
        if current_user.is_authenticated:
            return f(*args, **kwargs)
            
        # 로그인 시도 횟수 체크는 POST 요청에만 적용
        if request.method == 'POST':
            if session.get('login_attempts', 0) >= current_app.config['MAX_LOGIN_ATTEMPTS']:
                if 'login_blocked_until' not in session:
                    session['login_blocked_until'] = datetime.now().timestamp() + 1800  # 30분 블록
                elif datetime.now().timestamp() < session['login_blocked_until']:
                    remaining_time = int(session['login_blocked_until'] - datetime.now().timestamp())
                    remaining_minutes = remaining_time // 60
                    remaining_seconds = remaining_time % 60
                    flash(f'계정이 잠겼습니다. {remaining_minutes}분 {remaining_seconds}초 후에 다시 시도해주세요.', 'danger')
                    return render_template('auth/login.html', form=LoginForm())
                else:
                    # 잠금 시간이 지났으면 시도 횟수 초기화
                    session.pop('login_attempts', None)
                    session.pop('login_blocked_until', None)
        return f(*args, **kwargs)
    return decorated_function

@auth.route('/', methods=['GET', 'POST'])
@auth.route('/login', methods=['GET', 'POST'])
@check_login_attempts
def login():
    # GET 요청이면서 이미 로그인한 사용자는 급여관리 페이지로 리디렉션
    if request.method == 'GET' and current_user.is_authenticated:
        return redirect(url_for('payroll.index'))
        
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        
        # 사용자가 존재하지 않거나 비밀번호가 틀린 경우
        if not user or not user.check_password(form.password.data):
            session['login_attempts'] = session.get('login_attempts', 0) + 1
            remaining_attempts = current_app.config['MAX_LOGIN_ATTEMPTS'] - session['login_attempts']
            flash(f'아이디 또는 비밀번호가 올바르지 않습니다. (남은 시도 횟수: {remaining_attempts}회)', 'danger')
            return render_template('auth/login.html', form=form)
            
        # 계정이 잠겨있는 경우
        if user.is_locked():
            flash('계정이 잠겨있습니다. 잠시 후 다시 시도해주세요.', 'danger')
            return render_template('auth/login.html', form=form)
            
        # 계정이 비활성화된 경우
        if not user.is_active:
            flash('비활성화된 계정입니다. 관리자에게 문의하세요.', 'danger')
            return render_template('auth/login.html', form=form)
            
        # 로그인 성공
        if form.remember.data:
            # 30일 동안 로그인 유지
            session.permanent = True
            login_user(user, remember=True, 
                     duration=current_app.config['REMEMBER_COOKIE_DURATION'])
        else:
            # 브라우저 종료시까지만 유지
            session.permanent = False
            login_user(user, remember=False)
        
        # 로그인 관련 세션 데이터 초기화
        for key in ['login_attempts', 'login_blocked_until']:
            if key in session:
                session.pop(key)
        
        # 로그인 성공 로그 기록
        user.last_login = datetime.now()
        user.login_ip = request.remote_addr
        user.failed_login_attempts = 0  # 로그인 실패 횟수 초기화
        db.session.commit()
        
        # 원래 요청한 페이지로 리다이렉트
        next_page = request.args.get('next')
        if not next_page or not next_page.startswith('/'):
            next_page = url_for('payroll.index')
        return redirect(next_page)
            
    # GET 요청이거나 로그인 실패 시 로그인 페이지 표시
    return render_template('auth/login.html', form=form)

@auth.route('/dashboard')
@login_required
def dashboard():
    return render_template('auth/dashboard.html')

@auth.route('/logout')
@login_required
def logout():
    # 현재 사용자 로그아웃
    logout_user()
    
    # 세션 완전 초기화
    session.clear()
    
    flash('로그아웃되었습니다.', 'info')
    return redirect(url_for('auth.login'))

def send_reset_email(user, new_password):
    """임시 비밀번호 이메일 발송"""
    msg = MIMEMultipart()
    msg['Subject'] = '[우리소프트] 임시 비밀번호가 발급되었습니다'
    msg['From'] = current_app.config['SMTP_USERNAME']
    msg['To'] = user.email
    
    html = f"""
    <div style="font-family: 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif;">
        <h2>임시 비밀번호 발급</h2>
        <p>안녕하세요, {user.username}님.</p>
        <p>요청하신 임시 비밀번호가 발급되었습니다:</p>
        <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
            <strong style="font-size: 1.2em;">{new_password}</strong>
        </div>
        <p>보안을 위해 로그인 후 반드시 비밀번호를 변경해주세요.</p>
        <p style="color: #666; font-size: 0.9em; margin-top: 30px;">
            본 메일은 발신전용이며, 회신되지 않습니다.
        </p>
    </div>
    """
    
    msg.attach(MIMEText(html, 'html'))
    
    with smtplib.SMTP(current_app.config['SMTP_SERVER'], current_app.config['SMTP_PORT']) as server:
        server.starttls()
        server.login(current_app.config['SMTP_USERNAME'], current_app.config['SMTP_PASSWORD'])
        server.send_message(msg)

def generate_temp_password(length=12):
    """임시 비밀번호 생성"""
    characters = string.ascii_letters + string.digits + '!@#$%^&*'
    while True:
        password = ''.join(random.choice(characters) for i in range(length))
        # 최소 조건 검사
        if (any(c.islower() for c in password)  # 소문자
            and any(c.isupper() for c in password)  # 대문자
            and any(c.isdigit() for c in password)  # 숫자
            and any(c in '!@#$%^&*' for c in password)):  # 특수문자
            return password

@auth.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('payroll.index'))
        
    form = PasswordResetRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        
        if user and user.email == form.email.data:
            # 임시 비밀번호 생성
            temp_password = generate_temp_password()
            user.set_password(temp_password)
            db.session.commit()
            
            try:
                # 이메일 발송
                send_reset_email(user, temp_password)
                flash('임시 비밀번호가 이메일로 발송되었습니다. 이메일을 확인해주세요.', 'success')
                return redirect(url_for('auth.login'))
            except Exception as e:
                db.session.rollback()
                flash('이메일 발송 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.', 'danger')
        else:
            flash('입력하신 정보와 일치하는 계정을 찾을 수 없습니다.', 'danger')
            
    return render_template('auth/reset_password.html', form=form) 