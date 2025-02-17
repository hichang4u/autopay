from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, ValidationError
from app.models import User

class LoginForm(FlaskForm):
    username = StringField('아이디', validators=[DataRequired()])
    password = PasswordField('비밀번호', validators=[DataRequired()])
    remember = BooleanField('로그인 상태 유지')
    submit = SubmitField('로그인')

class PasswordResetRequestForm(FlaskForm):
    username = StringField('아이디', validators=[DataRequired()])
    email = StringField('이메일', validators=[DataRequired(), Email()])
    submit = SubmitField('임시 비밀번호 발급')
    
    def validate_email(self, field):
        user = User.query.filter_by(username=self.username.data).first()
        if not user or user.email != field.data:
            raise ValidationError('입력하신 정보와 일치하는 계정을 찾을 수 없습니다.') 