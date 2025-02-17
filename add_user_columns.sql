-- User 테이블에 name과 phone 컬럼 추가
ALTER TABLE user ADD COLUMN name VARCHAR(50);
ALTER TABLE user ADD COLUMN phone VARCHAR(20);

-- 기존 사용자의 name 컬럼을 username으로 초기화
UPDATE user SET name = username;

-- 기존 사용자의 phone 컬럼을 기본값으로 초기화
UPDATE user SET phone = '-'; 