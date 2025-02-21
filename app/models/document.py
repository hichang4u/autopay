from app import db
from datetime import datetime
from pytz import timezone
from . import get_korea_time
import logging

logger = logging.getLogger(__name__)

class DocumentTemplate(db.Model):
    __tablename__ = 'document_templates'
    
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(20), nullable=False)  # OFFICIAL, CERTIFICATE
    type = db.Column(db.String(50), nullable=False)  # OFFICIAL_NORMAL, CERT_EMPLOYMENT 등
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    content = db.Column(db.Text, nullable=False)  # HTML 템플릿 내용
    style = db.Column(db.JSON)  # 스타일 설정 (폰트, 크기 등)
    created_at = db.Column(db.DateTime, default=get_korea_time)
    created_by = db.Column(db.String(50))
    updated_at = db.Column(db.DateTime, onupdate=get_korea_time)
    updated_by = db.Column(db.String(50))
    is_active = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {
            'id': self.id,
            'category': self.category,
            'type': self.type,
            'name': self.name,
            'description': self.description,
            'content': self.content,
            'style': self.style,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'created_by': self.created_by,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None,
            'updated_by': self.updated_by
        }

class Document(db.Model):
    __tablename__ = 'documents'
    
    id = db.Column(db.Integer, primary_key=True)
    document_number = db.Column(db.String(20), unique=True)  # YYYYMMDD-XXX 형식
    category = db.Column(db.String(20), nullable=False)  # OFFICIAL, CERTIFICATE
    type = db.Column(db.String(50), nullable=False)  # OFFICIAL_NORMAL, CERT_EMPLOYMENT 등
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text)  # 공문 내용
    purpose = db.Column(db.String(200))  # 증명서 용도
    submit_to = db.Column(db.String(200))  # 증명서 제출처
    form_data = db.Column(db.JSON)  # 템플릿 기반 입력 데이터
    
    template_id = db.Column(db.Integer, db.ForeignKey('document_templates.id'))
    requester_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # nullable로 변경
    requester_email = db.Column(db.String(120))  # 비로그인 사용자용 이메일
    processor_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    status = db.Column(db.String(20), default='PENDING')  # PENDING, APPROVED, REJECTED, COMPLETED
    request_date = db.Column(db.DateTime, nullable=False, default=get_korea_time)
    process_date = db.Column(db.DateTime)
    process_comment = db.Column(db.Text)
    
    file_path = db.Column(db.String(255))  # 생성된 PDF 파일 경로
    preview_path = db.Column(db.String(255))  # 미리보기 파일 경로
    email_sent = db.Column(db.Boolean, default=False)
    email_receive = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=get_korea_time)
    updated_at = db.Column(db.DateTime, onupdate=get_korea_time)
    
    # 관계 설정
    template = db.relationship('DocumentTemplate', backref='documents')
    requester = db.relationship('User', foreign_keys=[requester_id], backref='requested_documents')
    processor = db.relationship('User', foreign_keys=[processor_id], backref='processed_documents')

    def to_dict(self):
        try:
            return {
                'id': self.id,
                'document_number': self.document_number,
                'category': self.category,
                'type': self.type,
                'title': self.title,
                'content': self.content,
                'purpose': self.purpose,
                'submit_to': self.submit_to,
                'form_data': self.form_data or {},
                'status': self.status,
                'request_date': self.request_date.strftime('%Y-%m-%d %H:%M:%S') if self.request_date else None,
                'process_date': self.process_date.strftime('%Y-%m-%d %H:%M:%S') if self.process_date else None,
                'process_comment': self.process_comment,
                'requester_name': self.requester.name if self.requester else '비회원',
                'requester_email': self.requester_email,
                'processor_name': self.processor.name if self.processor else None,
                'email_sent': self.email_sent,
                'email_receive': self.email_receive,
                'preview_path': self.preview_path,
                'file_path': self.file_path,
                'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
                'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None
            }
        except Exception as e:
            logger.error(f"Document to_dict 변환 중 오류 발생: {str(e)}")
            return {
                'id': self.id,
                'error': '문서 정보 변환 중 오류가 발생했습니다.'
            }

class DocumentHistory(db.Model):
    __tablename__ = 'document_history'
    
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=False)
    action = db.Column(db.String(50), nullable=False)  # REQUEST, APPROVE, REJECT, COMPLETE
    status = db.Column(db.String(20), nullable=False)
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=get_korea_time)
    created_by = db.Column(db.String(50))
    created_ip = db.Column(db.String(50))

    document = db.relationship('Document', backref='history') 