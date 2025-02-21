from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import Config
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)
    
    # 로그인 관리자 설정
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = '이 페이지에 접근하려면 로그인이 필요합니다.'
    login_manager.login_message_category = 'warning'
    login_manager.session_protection = 'strong'

    with app.app_context():
        # 모델 import
        from app.models import User
        from app.models.document import Document, DocumentTemplate, DocumentHistory
        
        @login_manager.user_loader
        def load_user(id):
            return User.query.get(int(id))

    from app.routes.auth import auth as auth_blueprint
    from app.routes.payroll import payroll as payroll_blueprint
    from app.routes.employee import employee as employee_blueprint
    from app.routes.document import document as document_blueprint

    app.register_blueprint(auth_blueprint)
    app.register_blueprint(payroll_blueprint)
    app.register_blueprint(employee_blueprint)
    app.register_blueprint(document_blueprint)

    return app

# 앱 인스턴스 생성
app = create_app()