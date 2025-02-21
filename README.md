# 급여관리 시스템

## 설치 방법

1. Python 가상환경 생성 및 활성화
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

2. 필요한 Python 패키지 설치
```bash
pip install -r requirements.txt
```

3. wkhtmltopdf 설치 (PDF 생성에 필요)
- Windows: [wkhtmltox-0.12.6-1.msvc2015-win64.exe](https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6-1/wkhtmltox-0.12.6-1.msvc2015-win64.exe) 다운로드 및 실행
- Mac: `brew install wkhtmltopdf`
- Linux: `sudo apt-get install wkhtmltopdf`

4. 프리텐다드 폰트 설치
- [Pretendard](https://github.com/orioncactus/pretendard/releases)에서 다운로드
- 다음 폰트 파일들을 `app/static/fonts/` 디렉토리에 복사:
  - Pretendard-Regular.ttf
  - Pretendard-Bold.ttf
  - Pretendard-Medium.ttf

## 환경 설정

1. `.env` 파일 생성
```
FLASK_APP=run.py
FLASK_ENV=development
SECRET_KEY=your-secret-key
```

2. 데이터베이스 초기화
```bash
flask db upgrade
python scripts/init_db.py
```

## 실행 방법

```bash
flask run
```

웹 브라우저에서 `http://localhost:5000` 접속

## 테스트 계정 생성

```bash
python create_test_user.py
```
테스트 계정 : test / Test1234!, wrsoft / Test1234!


## 주요 기능

- 급여 데이터 관리
- PDF 급여명세서 생성
- 이메일 발송
- 처리 이력 관리

