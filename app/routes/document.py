from flask import Blueprint, render_template, request, jsonify, current_app, send_file, url_for, session, render_template_string, flash, redirect
from flask_login import login_required, current_user
from app import db
from app.models.document import Document, DocumentTemplate, DocumentHistory
from app.utils.decorators import admin_required
from datetime import datetime
import os
from werkzeug.utils import secure_filename
import logging
import random
import pdfkit
from PyPDF2 import PdfReader, PdfWriter
from PIL import Image
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import sys
import traceback
import pytz
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
import re

# 로깅 설정
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app.log')
    ]
)
logger = logging.getLogger(__name__)

# 한국 시간 가져오기
def get_korea_time():
    """한국 시간을 반환합니다."""
    return datetime.now(pytz.timezone('Asia/Seoul'))

# 문서 분류 및 종류 정의
DOCUMENT_CATEGORIES = {
    'OFFICIAL': '공문',
    'CERTIFICATE': '증명서'
}

DOCUMENT_TYPES = {
    'OFFICIAL': {
        'OFFICIAL_NORMAL': '일반 공문',
        'OFFICIAL_REQUEST': '요청 공문',
        'OFFICIAL_REPORT': '보고 공문',
        'OFFICIAL_NOTICE': '통지 공문'
    },
    'CERTIFICATE': {
        'CERT_EMPLOYMENT': '재직증명서',
        'CERT_CAREER': '경력증명서',
        'CERT_SALARY': '급여확인서',
        'CERT_POSITION': '재직확인서'
    }
}

document = Blueprint('document', __name__)

# 이미지 업로드 설정
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_document_types(category=None):
    """문서 종류 목록 반환"""
    if category and category in DOCUMENT_TYPES:
        return DOCUMENT_TYPES[category]
    return DOCUMENT_TYPES

# 문서 신청 목록 페이지
@document.route('/document/request/list')
@login_required
def request_list():
    return render_template('document/request_list.html',
                         categories=DOCUMENT_CATEGORIES,
                         document_types=DOCUMENT_TYPES)

# 문서 신청 페이지
@document.route('/document/request')
def request_page():
    return render_template('document/request.html',
                         categories=DOCUMENT_CATEGORIES,
                         document_types=DOCUMENT_TYPES)

# 템플릿 관리 페이지
@document.route('/document/template')
@login_required
@admin_required
def template_page():
    return render_template('document/template.html',
                         categories=DOCUMENT_CATEGORIES,
                         document_types=DOCUMENT_TYPES)

# 문서 관리 페이지
@document.route('/document')
@login_required
@admin_required
def index():
    return render_template('document/document.html',
                         categories=DOCUMENT_CATEGORIES,
                         document_types=DOCUMENT_TYPES)

# 문서 신청 처리
@document.route('/document/request', methods=['POST'])
def request_document():
    try:
        data = request.get_json()
        
        # 필수 필드 검증
        required_fields = ['category', 'type', 'title', 'requestDate', 'email', 'template_id']
        if not all(field in data for field in required_fields):
            return jsonify({
                'success': False,
                'message': '필수 항목이 누락되었습니다.'
            }), 400
            
        # 템플릿 존재 여부 확인
        template = DocumentTemplate.query.get(data['template_id'])
        if not template:
            return jsonify({
                'success': False,
                'message': '선택한 템플릿을 찾을 수 없습니다.'
            }), 400
            
        # 비로그인 사용자의 경우 이메일을 세션에 저장
        if not current_user.is_authenticated:
            session['email'] = data['email']
            
        # 문서 생성
        doc = Document(
            category=data['category'],
            type=data['type'],
            title=data['title'],
            content=data.get('content'),
            purpose=data.get('purpose'),
            submit_to=data.get('submitTo'),
            template_id=data['template_id'],
            requester_id=current_user.id if current_user.is_authenticated else None,
            requester_email=data['email'],
            request_date=datetime.strptime(data['requestDate'], '%Y-%m-%d'),
            email_receive=data.get('emailReceive', True)
        )
        
        db.session.add(doc)
        
        # 이력 기록
        history = DocumentHistory(
            document=doc,
            action='REQUEST',
            status='PENDING',
            created_by=current_user.username if current_user.is_authenticated else '비회원',
            created_ip=request.remote_addr
        )
        db.session.add(history)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '문서가 성공적으로 신청되었습니다.',
            'data': {'id': doc.id}
        })
        
    except Exception as e:
        logger.error(f"문서 신청 중 오류 발생: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': '문서 신청 중 오류가 발생했습니다.'
        }), 500

# 내 신청 목록
@document.route('/document/my-requests')
def my_requests():
    try:
        logger.debug("문서 신청 목록 조회 시작")
        query = Document.query
        
        # 로그인한 사용자의 경우 requester_id로 조회
        if current_user.is_authenticated:
            logger.info(f"로그인 사용자({current_user.id})의 문서 목록 조회")
            query = query.filter_by(requester_id=current_user.id)
        # 비로그인 사용자의 경우 세션에 저장된 이메일로 조회
        else:
            email = session.get('email')
            logger.info(f"비로그인 사용자의 문서 목록 조회 (이메일: {email})")
            
            if not email:
                logger.warning("세션에 이메일 정보가 없음")
                return jsonify({
                    'success': True,
                    'data': [],
                    'message': '이메일 정보가 없습니다. 문서를 신청하면 내역이 표시됩니다.'
                })
                
            query = query.filter_by(requester_email=email)
            
        # 최신순 정렬
        try:
            docs = query.order_by(Document.request_date.desc()).all()
            logger.debug(f"조회된 문서 수: {len(docs)}개")
        except Exception as e:
            logger.error(f"데이터베이스 쿼리 실행 중 오류: {str(e)}")
            logger.error(traceback.format_exc())
            raise
        
        # 결과 변환 및 반환
        doc_list = []
        for doc in docs:
            try:
                logger.debug(f"문서 {doc.id} 변환 시작")
                doc_dict = doc.to_dict()
                
                if doc_dict and 'error' not in doc_dict:
                    # 문서 종류 이름 추가
                    doc_type_name = DOCUMENT_TYPES.get(doc.category, {}).get(doc.type, doc.type)
                    doc_dict['type_name'] = doc_type_name
                    doc_list.append(doc_dict)
                    logger.debug(f"문서 {doc.id} 변환 완료")
                else:
                    logger.warning(f"문서 {doc.id}의 변환 결과가 유효하지 않음: {doc_dict}")
            except Exception as e:
                logger.error(f"문서 {doc.id} 변환 중 오류: {str(e)}")
                logger.error(traceback.format_exc())
                continue
                
        logger.info(f"문서 목록 조회 완료 (총 {len(doc_list)}개)")
        return jsonify({
            'success': True,
            'data': doc_list,
            'total_count': len(doc_list)
        })
        
    except Exception as e:
        error_msg = f"신청 목록 조회 중 오류 발생: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        
        if current_app.debug:
            error_details = {
                'error': str(e),
                'traceback': traceback.format_exc()
            }
        else:
            error_details = None
            
        return jsonify({
            'success': False,
            'message': '신청 목록을 불러오는 중 오류가 발생했습니다.',
            'error_details': error_details
        }), 500

# 문서 목록 조회
@document.route('/document/list')
@document.route('/document/list/search')
def document_list_api():
    """문서 목록 API"""
    try:
        # 검색 조건
        category = request.args.get('category')
        status = request.args.get('status')
        keyword = request.args.get('keyword')
        
        # 기본 쿼리
        query = Document.query
        
        # 검색 조건 적용
        if category:
            query = query.filter(Document.category == category)
        if status:
            query = query.filter(Document.status == status)
        if keyword:
            query = query.filter(Document.title.like(f'%{keyword}%'))
        
        # 관리자가 아닌 경우 본인 문서만 조회
        if not current_user.is_authenticated or not current_user.is_admin:
            if current_user.is_authenticated:
                query = query.filter(Document.requester_id == current_user.id)
            elif 'email' in session:
                query = query.filter(Document.requester_email == session['email'])
            else:
                return jsonify({
                    'success': False,
                    'message': '로그인이 필요합니다.'
                }), 401
        
        # 최신순 정렬
        documents = query.order_by(Document.request_date.desc()).all()
        
        # 상태별 카운트
        counts = {
            'PENDING': Document.query.filter_by(status='PENDING').count(),
            'APPROVED': Document.query.filter_by(status='APPROVED').count(),
            'REJECTED': Document.query.filter_by(status='REJECTED').count(),
            'COMPLETED': Document.query.filter_by(status='COMPLETED').count()
        }
        
        # 결과 반환
        return jsonify({
            'success': True,
            'data': [doc.to_dict() for doc in documents],
            'counts': counts
        })
        
    except Exception as e:
        logger.error(f"문서 목록 조회 중 오류 발생: {str(e)}")
        return jsonify({
            'success': False,
            'message': '문서 목록을 불러오는 중 오류가 발생했습니다.',
            'error_details': str(e)
        }), 500

# 문서 승인 처리
@document.route('/document/approve/<int:id>', methods=['POST'])
@login_required
@admin_required
def approve_document(id):
    try:
        data = request.get_json()
        doc = Document.query.get_or_404(id)
        
        if doc.status != 'PENDING':
            return jsonify({
                'success': False,
                'message': '이미 처리된 문서입니다.'
            }), 400
            
        # 문서 승인 처리
        doc.status = 'APPROVED'
        doc.processor_id = current_user.id
        doc.process_date = get_korea_time()
        doc.process_comment = data.get('comment')
        
        # 문서 번호 생성 (제YYYY-MMDD순번두자리호 형식)
        now = get_korea_time()
        year = now.strftime('%Y')
        month_day = now.strftime('%m%d')
        
        # 오늘 생성된 문서 중 가장 큰 번호 찾기
        today_prefix = f'제{year}-{month_day}'
        latest_doc = Document.query.filter(
            Document.document_number.like(f'{today_prefix}%')
        ).order_by(Document.document_number.desc()).first()
        
        if latest_doc and latest_doc.document_number:
            try:
                # '제2023-0101XX호' 형식에서 XX 부분 추출
                last_seq_str = latest_doc.document_number.replace(today_prefix, '').replace('호', '')
                last_seq = int(last_seq_str)
                new_seq = last_seq + 1
            except (IndexError, ValueError):
                new_seq = 1
        else:
            new_seq = 1
        
        doc.document_number = f'제{year}-{month_day}{new_seq:02d}호'
        
        # 이력 기록
        history = DocumentHistory(
            document=doc,
            action='APPROVE',
            status='APPROVED',
            comment=data.get('comment'),
            created_by=current_user.username,
            created_ip=request.remote_addr
        )
        db.session.add(history)
        
        db.session.commit()
        
        # PDF 생성
        generate_pdf_document(doc)
        
        return jsonify({
            'success': True,
            'message': '문서가 승인되었습니다.',
            'data': {'document_number': doc.document_number}
        })
        
    except Exception as e:
        logger.error(f"문서 승인 중 오류 발생: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': '문서 승인 중 오류가 발생했습니다.'
        }), 500

def generate_pdf_document(doc):
    try:
        # PDF 파일 이름 생성
        filename = f"{doc.document_number}_{get_korea_time().strftime('%Y%m%d_%H%M%S')}.pdf"
        pdf_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'pdfs')
        os.makedirs(pdf_dir, exist_ok=True)
        pdf_path = os.path.join(pdf_dir, filename)

        # HTML 내용을 직접 사용
        html_content = doc.content

        # PDF 생성 옵션 설정
        options = {
            'page-size': 'A4',
            'margin-top': '20mm',
            'margin-right': '20mm',
            'margin-bottom': '20mm',
            'margin-left': '20mm',
            'encoding': 'UTF-8',
            'no-outline': None,
            'enable-local-file-access': None,
            'dpi': 300
        }
        
        # PDF 생성
        pdfkit.from_string(html_content, pdf_path, options=options)
        
        # 문서 상태 및 파일 경로 업데이트
        doc.status = 'COMPLETED'
        doc.file_path = os.path.join('pdfs', filename)
        doc.completed_date = get_korea_time()
        db.session.commit()
        
        # 이메일 발송
        send_document_email(doc)

        return True, "PDF가 성공적으로 생성되었습니다."
            
    except Exception as e:
        logger.error(f"PDF 생성 중 오류 발생: {str(e)}")
        logger.error(traceback.format_exc())
        return False, f"PDF 생성 중 오류가 발생했습니다: {str(e)}"

# 이메일 발송
def send_document_email(doc):
    try:
        msg = MIMEMultipart()
        msg['Subject'] = f'[우리소프트] 요청하신 문서가 발급되었습니다 ({doc.title})'
        msg['From'] = current_app.config['SMTP_USERNAME']
        msg['To'] = doc.requester_email
        
        # 이메일 본문
        html = f"""
        <div style="font-family: 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif;">
            <h2>문서 발급 완료</h2>
            <p>안녕하세요, 요청하신 문서가 발급되었습니다.</p>
            <p>
                <strong>문서 번호:</strong> {doc.document_number}<br>
                <strong>문서 제목:</strong> {doc.title}<br>
                <strong>발급 일자:</strong> {doc.process_date.strftime('%Y-%m-%d %H:%M:%S')}
            </p>
            <p>첨부된 PDF 파일을 확인해주세요.</p>
        </div>
        """
        
        msg.attach(MIMEText(html, 'html'))
        
        # PDF 첨부
        pdf_path = os.path.join(current_app.root_path, 'static', doc.file_path)
        with open(pdf_path, 'rb') as f:
            pdf = MIMEApplication(f.read(), _subtype='pdf')
            pdf.add_header(
                'Content-Disposition',
                'attachment',
                filename=os.path.basename(doc.file_path)
            )
            msg.attach(pdf)
        
        # 이메일 발송
        with smtplib.SMTP(current_app.config['SMTP_SERVER'], current_app.config['SMTP_PORT']) as server:
            server.starttls()
            server.login(current_app.config['SMTP_USERNAME'], current_app.config['SMTP_PASSWORD'])
            server.send_message(msg)
            
        # 이메일 발송 상태 업데이트
        doc.email_sent = True
        db.session.commit()
        
    except Exception as e:
        logger.error(f"이메일 발송 중 오류 발생: {str(e)}")
        raise

# 문서 처리 (승인/반려)
@document.route('/document/process/<int:id>', methods=['POST'])
@login_required
@admin_required
def process_document(id):
    try:
        data = request.get_json()
        status = data.get('status')
        comment = data.get('comment')
        
        if not status or status not in ['APPROVED', 'REJECTED']:
            return jsonify({
                'success': False,
                'message': '올바르지 않은 처리상태입니다.'
            }), 400
            
        doc = Document.query.get_or_404(id)
        
        # 이미 처리된 문서인지 확인
        if doc.status != 'PENDING':
            return jsonify({
                'success': False,
                'message': '이미 처리된 문서입니다.'
            }), 400
            
        # 문서 상태 업데이트
        doc.status = status
        doc.processor_id = current_user.id
        doc.process_date = datetime.now()
        doc.process_comment = comment
        
        # 승인된 경우 문서 번호 생성
        if status == 'APPROVED' and not doc.document_number:
            now = datetime.now()
            year = now.strftime('%Y')
            month_day = now.strftime('%m%d')
            
            # 오늘 생성된 문서 중 가장 큰 번호 찾기
            today_prefix = f'제{year}-{month_day}'
            latest_doc = Document.query.filter(
                Document.document_number.like(f'{today_prefix}%')
            ).order_by(db.desc(Document.document_number)).first()
            
            if latest_doc and latest_doc.document_number:
                # 마지막 번호에서 순번 추출하여 1 증가
                try:
                    # '제2023-0101XX호' 형식에서 XX 부분 추출
                    last_seq_str = latest_doc.document_number.replace(today_prefix, '').replace('호', '')
                    last_seq = int(last_seq_str)
                    new_seq = last_seq + 1
                except (IndexError, ValueError):
                    new_seq = 1
            else:
                new_seq = 1
                
            # 새 문서 번호 생성 (제YYYY-MMDD순번두자리호 형식)
            doc.document_number = f'제{year}-{month_day}{new_seq:02d}호'
            logger.info(f"문서 번호 생성: {doc.document_number}")
        
        # 이력 기록
        history = DocumentHistory(
            document=doc,
            action='APPROVE' if status == 'APPROVED' else 'REJECT',
            status=status,
            comment=comment,
            created_by=current_user.username,
            created_ip=request.remote_addr
        )
        db.session.add(history)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '문서가 처리되었습니다.'
        })
        
    except Exception as e:
        logger.error(f"문서 처리 중 오류 발생: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': '문서 처리 중 오류가 발생했습니다.'
        }), 500

# 템플릿 목록 페이지
@document.route('/document/template/list')
@login_required
@admin_required
def template_list():
    """템플릿 목록 페이지"""
    return render_template('document/template_list.html', 
                         categories=DOCUMENT_CATEGORIES,
                         document_types=DOCUMENT_TYPES)

# 새 템플릿 페이지
@document.route('/document/template/create')
@login_required
@admin_required
def template_create():
    return render_template('document/template_form.html',
                         categories=DOCUMENT_CATEGORIES,
                         document_types=DOCUMENT_TYPES)

# 템플릿 수정 페이지
@document.route('/document/template/edit/<int:id>')
@login_required
@admin_required
def template_edit(id):
    template = DocumentTemplate.query.get_or_404(id)
    return render_template('document/template_form.html',
                         template=template,
                         categories=DOCUMENT_CATEGORIES,
                         document_types=DOCUMENT_TYPES)

# 템플릿 저장
@document.route('/document/template/save', methods=['POST'])
@login_required
@admin_required
def save_template():
    try:
        data = request.get_json()
        
        # 필수 필드 검증
        required_fields = ['category', 'type', 'name', 'content', 'pdf_template']
        if not all(field in data for field in required_fields):
            return jsonify({
                'success': False,
                'message': '필수 항목이 누락되었습니다.'
            }), 400
            
        # 템플릿 정보 저장
        template = DocumentTemplate(
            category=data['category'],
            type=data['type'],
            name=data['name'],
            description=data.get('description'),
            content=data['content'],
            style=data.get('style'),
            pdf_template=data['pdf_template'],
            variables=data.get('variables', []),
            created_by=current_user.username
        )
        
        db.session.add(template)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '템플릿이 저장되었습니다.',
            'data': template.to_dict()
        })
        
    except Exception as e:
        logger.error(f"템플릿 저장 중 오류 발생: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': '템플릿 저장 중 오류가 발생했습니다.'
        }), 500

# 템플릿 수정
@document.route('/document/template/update/<int:id>', methods=['PUT'])
@login_required
@admin_required
def update_template(id):
    try:
        template = DocumentTemplate.query.get_or_404(id)
        data = request.get_json()
        
        # 필수 필드 검증
        required_fields = ['category', 'type', 'name', 'content', 'pdf_template']
        if not all(field in data for field in required_fields):
            return jsonify({
                'success': False,
                'message': '필수 항목이 누락되었습니다.'
            }), 400
            
        # 템플릿 정보 업데이트
        template.category = data['category']
        template.type = data['type']
        template.name = data['name']
        template.description = data.get('description')
        template.content = data['content']
        template.style = data.get('style')
        template.pdf_template = data['pdf_template']
        template.variables = data.get('variables', [])
        template.updated_by = current_user.username
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '템플릿이 수정되었습니다.',
            'data': template.to_dict()
        })
        
    except Exception as e:
        logger.error(f"템플릿 수정 중 오류 발생: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': '템플릿 수정 중 오류가 발생했습니다.'
        }), 500

# 템플릿 다운로드
@document.route('/document/template/download/<int:id>')
@login_required
@admin_required
def download_template(id):
    try:
        template = DocumentTemplate.query.get_or_404(id)
        file_path = os.path.join(current_app.root_path, 'static', template.file_path)
        
        if not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'message': '템플릿 파일을 찾을 수 없습니다.'
            }), 404
            
        return send_file(
            file_path,
            as_attachment=True,
            download_name=os.path.basename(template.file_path)
        )
        
    except Exception as e:
        logger.error(f"템플릿 다운로드 중 오류 발생: {str(e)}")
        return jsonify({
            'success': False,
            'message': '템플릿 다운로드 중 오류가 발생했습니다.'
        }), 500

# 템플릿 삭제
@document.route('/document/template/delete/<int:id>', methods=['DELETE'])
@login_required
@admin_required
def delete_template(id):
    try:
        template = DocumentTemplate.query.get_or_404(id)
        
        # 소프트 삭제 (is_active만 False로 변경)
        template.is_active = False
        template.updated_by = current_user.username
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '템플릿이 삭제되었습니다.'
        })
        
    except Exception as e:
        logger.error(f"템플릿 삭제 중 오류 발생: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': '템플릿 삭제 중 오류가 발생했습니다.'
        }), 500

# 문서 검색
@document.route('/document/search')
@login_required
@admin_required
def search_documents():
    try:
        status = request.args.get('status')
        category = request.args.get('category')
        keyword = request.args.get('keyword')
        
        query = Document.query
        
        if status:
            query = query.filter(Document.status == status)
        if category:
            query = query.filter(Document.category == category)
        if keyword:
            query = query.filter(
                db.or_(
                    Document.title.ilike(f'%{keyword}%'),
                    Document.document_number.ilike(f'%{keyword}%')
                )
            )
            
        docs = query.order_by(Document.request_date.desc()).all()
        
        # 상태별 건수
        counts = {
            'pending': sum(1 for doc in docs if doc.status == 'PENDING'),
            'approved': sum(1 for doc in docs if doc.status == 'APPROVED'),
            'completed': sum(1 for doc in docs if doc.status == 'COMPLETED'),
            'rejected': sum(1 for doc in docs if doc.status == 'REJECTED')
        }
        
        return jsonify({
            'success': True,
            'data': [doc.to_dict() for doc in docs],
            'counts': counts
        })
        
    except Exception as e:
        logger.error(f"문서 검색 중 오류 발생: {str(e)}")
        return jsonify({
            'success': False,
            'message': '문서 검색 중 오류가 발생했습니다.'
        }), 500

# 신청 취소
@document.route('/document/cancel/<int:id>', methods=['POST'])
@login_required
def cancel_request(id):
    try:
        doc = Document.query.get_or_404(id)
        
        # 본인 문서인지 확인
        if doc.requester_id != current_user.id:
            return jsonify({
                'success': False,
                'message': '본인의 문서만 취소할 수 있습니다.'
            }), 403
            
        # 대기중인 문서인지 확인
        if doc.status != 'PENDING':
            return jsonify({
                'success': False,
                'message': '대기중인 문서만 취소할 수 있습니다.'
            }), 400
            
        # 문서 상태 변경
        doc.status = 'CANCELED'
        
        # 이력 기록
        history = DocumentHistory(
            document=doc,
            action='CANCEL',
            status='CANCELED',
            created_by=current_user.username,
            created_ip=request.remote_addr
        )
        db.session.add(history)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '문서가 취소되었습니다.'
        })
        
    except Exception as e:
        logger.error(f"문서 취소 중 오류 발생: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': '문서 취소 중 오류가 발생했습니다.'
        }), 500

# 템플릿 조회
@document.route('/document/template/<string:category>/<string:type>')
@document.route('/document/template/<int:id>')
def get_template(category=None, type=None, id=None):
    """템플릿 정보 조회"""
    try:
        if id:
            template = DocumentTemplate.query.get_or_404(id)
        else:
            template = DocumentTemplate.query.filter_by(
                category=category,
                type=type,
                is_active=True
            ).first()
            
        if not template:
            return jsonify({
                'success': False,
                'message': '템플릿을 찾을 수 없습니다.'
            }), 404
            
        return jsonify({
            'success': True,
            'data': template.to_dict()
        })
        
    except Exception as e:
        logger.error(f"템플릿 조회 중 오류 발생: {str(e)}")
        return jsonify({
            'success': False,
            'message': '템플릿 조회 중 오류가 발생했습니다.'
        }), 500

# 문서 미리보기 생성
@document.route('/document/preview', methods=['POST'])
@login_required
@admin_required
def preview_template():
    try:
        data = request.get_json()
        template_name = data.get('template_name')
        sample_data = data.get('sample_data')

        # 템플릿 파일 읽기
        template_path = os.path.join(current_app.root_path, 'templates', 'document', 'pdf_templates', f'{template_name}.html')
        if not os.path.exists(template_path):
            return jsonify({
                'success': False,
                'message': '템플릿을 찾을 수 없습니다.'
            }), 404

        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()

        # Jinja2 템플릿 렌더링
        template = current_app.jinja_env.from_string(template_content)
        rendered_html = template.render(**sample_data)

        return jsonify({
            'success': True,
            'html': rendered_html
        })
    except Exception as e:
        logger.error(f"템플릿 미리보기 생성 중 오류 발생: {str(e)}")
        return jsonify({
            'success': False,
            'message': '미리보기를 생성하는 중 오류가 발생했습니다.'
        }), 500

# 이미지 업로드
@document.route('/document/upload-image', methods=['POST'])
@login_required
@admin_required
def upload_image():
    try:
        if 'image' not in request.files:
            return jsonify({
                'success': False,
                'message': '이미지 파일이 없습니다.'
            }), 400
            
        file = request.files['image']
        if file.filename == '':
            return jsonify({
                'success': False,
                'message': '선택된 파일이 없습니다.'
            }), 400
            
        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'message': '허용되지 않는 파일 형식입니다.'
            }), 400
            
        # 업로드 폴더가 없으면 생성
        if not os.path.exists(UPLOAD_FOLDER):
            os.makedirs(UPLOAD_FOLDER)
            
        # 파일명 생성 (timestamp + secure_filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{secure_filename(file.filename)}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        
        # 파일 저장
        file.save(filepath)
        
        # 상대 URL 경로 반환
        url = f"/static/uploads/{filename}"
        
        return jsonify({
            'success': True,
            'message': '이미지가 업로드되었습니다.',
            'data': {
                'url': url,
                'filename': filename
            }
        })
        
    except Exception as e:
        logger.error(f"이미지 업로드 중 오류 발생: {str(e)}")
        return jsonify({
            'success': False,
            'message': '이미지 업로드 중 오류가 발생했습니다.'
        }), 500

@document.route('/template/form')
@login_required
@admin_required
def template_form():
    """템플릿 등록/수정 페이지"""
    template_id = request.args.get('id', type=int)
    template = None
    if template_id:
        template = DocumentTemplate.query.get_or_404(template_id)
    
    return render_template('document/template_form.html',
                         template=template,
                         categories=DOCUMENT_CATEGORIES,
                         types=DOCUMENT_TYPES)

# 템플릿 목록 조회
@document.route('/document/templates')
@login_required
@admin_required
def get_templates():
    try:
        category = request.args.get('category')
        keyword = request.args.get('keyword')
        
        query = DocumentTemplate.query.filter_by(is_active=True)
        
        if category:
            query = query.filter(DocumentTemplate.category == category)
        if keyword:
            query = query.filter(
                db.or_(
                    DocumentTemplate.name.ilike(f'%{keyword}%'),
                    DocumentTemplate.description.ilike(f'%{keyword}%')
                )
            )
            
        templates = query.order_by(DocumentTemplate.created_at.desc()).all()
        
        return jsonify({
            'success': True,
            'data': [template.to_dict() for template in templates]
        })
        
    except Exception as e:
        logger.error(f"템플릿 목록 조회 중 오류 발생: {str(e)}")
        return jsonify({
            'success': False,
            'message': '템플릿 목록을 불러오는 중 오류가 발생했습니다.'
        }), 500

# 템플릿 목록 검색
@document.route('/document/template/list/search')
@login_required
@admin_required
def search_templates():
    try:
        category = request.args.get('category')
        keyword = request.args.get('keyword')
        
        # 기본 쿼리: 활성화된 템플릿만 조회
        query = DocumentTemplate.query.filter_by(is_active=True)
        
        # 필터 적용
        if category:
            query = query.filter(DocumentTemplate.category == category)
        if keyword:
            query = query.filter(
                db.or_(
                    DocumentTemplate.name.ilike(f'%{keyword}%'),
                    DocumentTemplate.description.ilike(f'%{keyword}%')
                )
            )
            
        # 정렬: 최신순
        query = query.order_by(DocumentTemplate.created_at.desc())
        
        # 결과 조회
        templates = query.all()
        
        return jsonify({
            'success': True,
            'data': [template.to_dict() for template in templates]
        })
        
    except Exception as e:
        logger.error(f"템플릿 목록 검색 중 오류 발생: {str(e)}")
        return jsonify({
            'success': False,
            'message': '템플릿 목록을 불러오는 중 오류가 발생했습니다.'
        }), 500

# 문서 상세 정보 조회 (관리자용)
@document.route('/document/<int:id>')
@login_required
@admin_required
def get_document(id):
    try:
        doc = Document.query.get_or_404(id)
        return jsonify({
            'success': True,
            'data': doc.to_dict()
        })
    except Exception as e:
        logger.error(f"문서 상세정보 조회 중 오류 발생: {str(e)}")
        return jsonify({
            'success': False,
            'message': '문서 정보를 불러오는 중 오류가 발생했습니다.'
        }), 500

# 사용자 문서 상세 정보 조회 (일반 사용자용)
@document.route('/document/user/<int:id>')
def get_user_document(id):
    try:
        doc = Document.query.get_or_404(id)
        
        # 권한 확인: 로그인한 사용자의 문서이거나 세션의 이메일과 일치하는 문서만 조회 가능
        if current_user.is_authenticated:
            if doc.requester_id != current_user.id and not current_user.is_admin:
                return jsonify({
                    'success': False,
                    'message': '해당 문서에 접근할 권한이 없습니다.'
                }), 403
        else:
            # 비로그인 사용자는 세션의 이메일과 일치하는 문서만 조회 가능
            email = session.get('email')
            if not email or doc.requester_email != email:
                return jsonify({
                    'success': False,
                    'message': '해당 문서에 접근할 권한이 없습니다.'
                }), 403
        
        return jsonify({
            'success': True,
            'data': doc.to_dict()
        })
    except Exception as e:
        logger.error(f"사용자 문서 상세정보 조회 중 오류 발생: {str(e)}")
        return jsonify({
            'success': False,
            'message': '문서 정보를 불러오는 중 오류가 발생했습니다.'
        }), 500

# PDF 생성 엔드포인트
@document.route('/document/generate-pdf/<int:id>', methods=['POST'])
@login_required
@admin_required
def generate_pdf(id):
    try:
        # 문서 정보 조회
        doc = Document.query.get_or_404(id)
        if doc.status != 'APPROVED':
            return jsonify({
                'success': False,
                'message': '승인된 문서만 PDF 생성이 가능합니다.'
            }), 400

        # PDF 파일명 생성 (문서번호.pdf)
        filename = f"{doc.document_number}.pdf"
        
        # PDF 저장 디렉토리 생성
        relative_dir = 'pdfs'
        pdf_dir = os.path.join(current_app.root_path, 'static', relative_dir)
        os.makedirs(pdf_dir, exist_ok=True)
        
        # 파일 경로 설정
        file_path = f'{relative_dir}/{filename}'
        absolute_path = os.path.join(current_app.root_path, 'static', relative_dir, filename)

        try:
            logger.info("PDF 생성 시작")
            
            # 템플릿 정보 가져오기
            template = DocumentTemplate.query.get(doc.template_id)
            if not template:
                raise ValueError('템플릿을 찾을 수 없습니다.')

            # 템플릿 파일 읽기
            template_path = os.path.join(current_app.root_path, 'templates', 'document', 'pdf_templates', f'{template.pdf_template}.html')
            if not os.path.exists(template_path):
                raise ValueError('PDF 템플릿 파일을 찾을 수 없습니다.')

            # PDF 데이터 준비
            template_variables = {}
            
            # 템플릿 변수 처리 (리스트 또는 딕셔너리 형태)
            if template and template.variables:
                if isinstance(template.variables, list):
                    logger.info("템플릿 변수가 리스트 형태로 저장되어 있어 딕셔너리로 변환합니다.")
                    for var in template.variables:
                        if isinstance(var, dict) and 'name' in var:
                            template_variables[var['name']] = var.get('value', '')
                elif isinstance(template.variables, dict):
                    template_variables = template.variables
            
            # 필수 변수 기본값 설정 (없을 경우)
            if 'recipient' not in template_variables:
                template_variables['recipient'] = "-"
            if 'reference' not in template_variables:
                template_variables['reference'] = "-"
            if 'title' not in template_variables:
                template_variables['title'] = doc.title

            # 안전한 URL 경로로 수정
            host_url = request.host_url.rstrip('/')
            app_root = current_app.config.get('APPLICATION_ROOT', '')
            if app_root:
                base_url = f"{host_url}/{app_root.strip('/')}"
            else:
                base_url = host_url

            # 로컬 경로로 템플릿의 리소스 참조 처리
            static_dir = os.path.join(current_app.root_path, 'static')
            # 백슬래시를 슬래시로 변환
            static_dir_path = static_dir.replace('\\', '/')

            pdf_data = {
                'document_number': doc.document_number,
                'title': doc.title,
                'request_date': doc.request_date.strftime('%Y년 %m월 %d일') if doc.request_date else None,
                'process_date': doc.process_date.strftime('%Y년 %m월 %d일') if doc.process_date else None,
                'content': doc.content,
                'purpose': doc.purpose,
                'submit_to': doc.submit_to,
                'variables': template_variables,
                'static_url': "file:///" + static_dir_path + "/"
            }
            
            # 템플릿 렌더링
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
                
            # url_for 함수를 대체하는 사용자 정의 함수
            def static_url(filename):
                path = os.path.join(static_dir, filename).replace('\\', '/')
                return "file:///" + path
            
            # 기존 url_for 함수 저장
            original_url_for = current_app.jinja_env.globals.get('url_for')
            
            try:
                # url_for 함수 대체
                current_app.jinja_env.globals['url_for'] = lambda endpoint, **kwargs: static_url(kwargs['filename']) if endpoint == 'static' else ''
                
                template = current_app.jinja_env.from_string(template_content)
                rendered_html = template.render(**pdf_data)
                
                # PDF 생성 옵션 설정 - A4 용지 규격에 맞게 설정
                options = {
                    'encoding': 'UTF-8',
                    'enable-local-file-access': None,
                    'allow': [static_dir_path],
                    'margin-top': '20mm',
                    'margin-right': '20mm',
                    'margin-bottom': '20mm',
                    'margin-left': '20mm',
                    'page-size': 'A4',
                    'dpi': '300',
                    'no-stop-slow-scripts': None,
                    'debug-javascript': None,
                    'javascript-delay': '1000',
                    'load-error-handling': 'ignore',
                    'zoom': '1.0',
                    'orientation': 'Portrait',
                    'print-media-type': None
                }
                
                # PDF 생성
                config = pdfkit.configuration(wkhtmltopdf=r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe')
                pdfkit.from_string(rendered_html, absolute_path, options=options, configuration=config)
                logger.info(f"PDF 파일 생성 완료: {absolute_path}")
            finally:
                # 원래의 url_for 함수 복원
                if original_url_for:
                    current_app.jinja_env.globals['url_for'] = original_url_for
                else:
                    # Flask 기본 url_for로 복원
                    from flask import url_for as flask_url_for
                    current_app.jinja_env.globals['url_for'] = flask_url_for

            # 문서 상태 업데이트
            doc.status = 'COMPLETED'
            doc.file_path = file_path
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'PDF가 생성되었습니다.',
                'file_path': file_path
            })

        except Exception as e:
            logger.error(f"PDF 생성 중 오류 발생: {str(e)}")
            logger.error(traceback.format_exc())
            return jsonify({
                'success': False,
                'message': 'PDF 생성 중 오류가 발생했습니다.',
                'error': str(e),
                'error_detail': traceback.format_exc() if current_app.debug else None
            }), 500

    except Exception as e:
        logger.error(f"PDF 생성 중 오류 발생: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'PDF 생성 중 오류가 발생했습니다.',
            'error': str(e),
            'error_detail': traceback.format_exc() if current_app.debug else None
        }), 500

@document.route('/document/preview/<int:document_id>')
@login_required
def preview_pdf(document_id):
    try:
        # 문서 정보 조회
        doc = Document.query.get_or_404(document_id)
        
        if doc.status != 'COMPLETED':
            flash('PDF가 아직 생성되지 않았습니다.', 'warning')
            return redirect(url_for('document.index'))
            
        # PDF 파일 경로 가져오기
        if not doc.file_path:
            flash('PDF 파일을 찾을 수 없습니다.', 'error')
            return redirect(url_for('document.index'))
            
        # 파일 존재 여부 확인 (경로 구분자 통일)
        pdf_path = os.path.join(current_app.root_path, 'static', doc.file_path.replace('\\', '/'))
        if not os.path.exists(pdf_path):
            flash('PDF 파일을 찾을 수 없습니다.', 'error')
            return redirect(url_for('document.index'))
            
        return render_template('document/preview.html', 
            document=doc)
            
    except Exception as e:
        current_app.logger.error(f'PDF 미리보기 중 오류 발생: {str(e)}')
        flash('PDF 미리보기 중 오류가 발생했습니다.', 'error')
        return redirect(url_for('document.index'))

@document.route('/document/pdf-template/<template_name>')
@login_required
@admin_required
def get_pdf_template(template_name):
    try:
        templates = {
            'default': 'pdf_templates/default.html',
            'certificate': 'pdf_templates/certificate.html',
            'official': 'pdf_templates/official.html'
        }
        
        if template_name not in templates:
            return jsonify({
                'success': False,
                'message': '존재하지 않는 템플릿입니다.'
            }), 404
            
        template_path = os.path.join(current_app.root_path, 'templates', 'document', templates[template_name])
        
        if not os.path.exists(template_path):
            return jsonify({
                'success': False,
                'message': '템플릿 파일을 찾을 수 없습니다.'
            }), 404
            
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        return jsonify({
            'success': True,
            'content': content
        })
        
    except Exception as e:
        logger.error(f"PDF 템플릿 로드 중 오류 발생: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'PDF 템플릿을 불러오는 중 오류가 발생했습니다.'
        }), 500 