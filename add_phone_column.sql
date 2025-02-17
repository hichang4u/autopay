-- User 테이블에 name과 phone 컬럼 추가
ALTER TABLE user ADD COLUMN name VARCHAR(50);
ALTER TABLE user ADD COLUMN phone VARCHAR(20);

-- 기존 사용자의 name과 phone 컬럼을 기본값으로 업데이트
UPDATE user SET name = username;
UPDATE user SET phone = '-'; 