-- PayrollDetail 테이블의 created_by, updated_by 컬럼 업데이트
UPDATE payroll_detail pd 
SET created_by = (SELECT name FROM user WHERE username = pd.created_by)
WHERE created_by IS NOT NULL;

UPDATE payroll_detail pd 
SET updated_by = (SELECT name FROM user WHERE username = pd.updated_by)
WHERE updated_by IS NOT NULL;

-- PayrollRecord 테이블의 created_by, updated_by 컬럼 업데이트
UPDATE payroll_record pr 
SET created_by = (SELECT name FROM user WHERE username = pr.created_by)
WHERE created_by IS NOT NULL;

UPDATE payroll_record pr 
SET updated_by = (SELECT name FROM user WHERE username = pr.updated_by)
WHERE updated_by IS NOT NULL;

-- Employee 테이블의 created_by, updated_by 컬럼 업데이트
UPDATE employee e 
SET created_by = (SELECT name FROM user WHERE username = e.created_by)
WHERE created_by IS NOT NULL;

UPDATE employee e 
SET updated_by = (SELECT name FROM user WHERE username = e.updated_by)
WHERE updated_by IS NOT NULL; 