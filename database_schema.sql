-- 사용자 테이블
CREATE TABLE IF NOT EXISTS user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT,
    email TEXT UNIQUE,
    is_active INTEGER DEFAULT 1,
    is_admin INTEGER DEFAULT 0,
    last_login TEXT,
    login_ip TEXT,
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until TEXT,
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT
);

-- 코드 그룹 테이블
CREATE TABLE IF NOT EXISTS code_groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_code TEXT NOT NULL UNIQUE,
    group_name TEXT NOT NULL,
    use_yn TEXT DEFAULT 'Y',
    created_at TEXT DEFAULT (datetime('now', 'localtime'))
);

-- 코드 테이블
CREATE TABLE IF NOT EXISTS codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_code TEXT NOT NULL,
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    order_seq INTEGER DEFAULT 0,
    use_yn TEXT DEFAULT 'Y',
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    UNIQUE(group_code, code)
);

-- 직원 테이블
CREATE TABLE IF NOT EXISTS employee (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    emp_number TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    birth_date TEXT,
    join_date TEXT,
    position TEXT,
    department TEXT,
    email TEXT UNIQUE,
    pdf_password TEXT,
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    created_by TEXT,
    created_ip TEXT,
    updated_at TEXT,
    updated_by TEXT,
    updated_ip TEXT
);

-- 직원 이력 테이블
CREATE TABLE IF NOT EXISTS employee_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL,
    field_name TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    changed_by TEXT,
    changed_at TEXT DEFAULT (datetime('now', 'localtime')),
    changed_ip TEXT,
    FOREIGN KEY (employee_id) REFERENCES employee(id)
);

-- 급여 테이블
CREATE TABLE IF NOT EXISTS salary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    emp_id INTEGER NOT NULL,
    payment_date TEXT NOT NULL,
    base_salary INTEGER,
    position_bonus INTEGER,
    overtime_pay INTEGER,
    meal_allowance INTEGER,
    FOREIGN KEY (emp_id) REFERENCES employee(id)
);

-- 급여 기록 테이블
CREATE TABLE IF NOT EXISTS payroll_record (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pay_year_month TEXT NOT NULL,  -- YYYY-MM 형식
    payment_date TEXT NOT NULL,
    status TEXT DEFAULT 'TEMP_SAVE',
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    created_by TEXT,
    created_ip TEXT,
    updated_at TEXT,
    updated_by TEXT,
    updated_ip TEXT
);

-- 급여 상세 테이블
CREATE TABLE IF NOT EXISTS payroll_detail (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id INTEGER NOT NULL,
    employee_id TEXT NOT NULL,
    employee_name TEXT NOT NULL,
    department TEXT,
    position TEXT,
    
    -- 지급 항목
    base_salary INTEGER DEFAULT 0,
    position_allowance INTEGER DEFAULT 0,
    meal_allowance INTEGER DEFAULT 0,
    car_allowance INTEGER DEFAULT 0,
    total_payment INTEGER DEFAULT 0,
    
    -- 공제 항목
    income_tax INTEGER DEFAULT 0,
    local_income_tax INTEGER DEFAULT 0,
    national_pension INTEGER DEFAULT 0,
    health_insurance INTEGER DEFAULT 0,
    long_term_care INTEGER DEFAULT 0,
    employment_insurance INTEGER DEFAULT 0,
    total_deduction INTEGER DEFAULT 0,
    
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (record_id) REFERENCES payroll_record(id) ON DELETE CASCADE
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_user_username ON user(username);
CREATE INDEX IF NOT EXISTS idx_user_email ON user(email);
CREATE INDEX IF NOT EXISTS idx_user_last_login ON user(last_login);

CREATE INDEX IF NOT EXISTS idx_code_groups_group_code ON code_groups(group_code);
CREATE INDEX IF NOT EXISTS idx_codes_group_code ON codes(group_code);
CREATE INDEX IF NOT EXISTS idx_codes_code ON codes(code);
CREATE INDEX IF NOT EXISTS idx_codes_order_seq ON codes(order_seq);

CREATE INDEX IF NOT EXISTS idx_employee_emp_number ON employee(emp_number);
CREATE INDEX IF NOT EXISTS idx_employee_email ON employee(email);
CREATE INDEX IF NOT EXISTS idx_employee_position ON employee(position);
CREATE INDEX IF NOT EXISTS idx_employee_join_date ON employee(join_date);

CREATE INDEX IF NOT EXISTS idx_employee_history_employee_id ON employee_history(employee_id);
CREATE INDEX IF NOT EXISTS idx_employee_history_changed_at ON employee_history(changed_at);

CREATE INDEX IF NOT EXISTS idx_salary_emp_id ON salary(emp_id);
CREATE INDEX IF NOT EXISTS idx_salary_payment_date ON salary(payment_date);

CREATE INDEX IF NOT EXISTS idx_payroll_record_pay_year_month ON payroll_record(pay_year_month);
CREATE INDEX IF NOT EXISTS idx_payroll_record_payment_date ON payroll_record(payment_date);
CREATE INDEX IF NOT EXISTS idx_payroll_record_status ON payroll_record(status);

CREATE INDEX IF NOT EXISTS idx_payroll_detail_record_id ON payroll_detail(record_id);
CREATE INDEX IF NOT EXISTS idx_payroll_detail_employee_id ON payroll_detail(employee_id);

-- 뷰 생성 (급여 통계용)
CREATE VIEW IF NOT EXISTS v_payroll_summary AS
SELECT 
    pr.pay_year_month,
    pr.payment_date,
    COUNT(pd.id) as employee_count,
    SUM(pd.total_payment) as total_payment_amount,
    SUM(pd.total_deduction) as total_deduction_amount,
    SUM(pd.total_payment - pd.total_deduction) as total_net_amount,
    pr.status,
    c.name as status_name
FROM payroll_record pr
LEFT JOIN payroll_detail pd ON pr.id = pd.record_id
LEFT JOIN codes c ON pr.status = c.code AND c.group_code = 'PAYROLL_STATUS'
GROUP BY pr.id, pr.pay_year_month, pr.payment_date, pr.status, c.name;

-- 초기 데이터 삽입
INSERT OR IGNORE INTO code_groups (group_code, group_name)
VALUES ('PAYROLL_STATUS', '급여처리상태');

INSERT OR IGNORE INTO codes (group_code, code, name, order_seq)
VALUES 
    ('PAYROLL_STATUS', 'TEMP_SAVE', '임시저장', 1),
    ('PAYROLL_STATUS', 'PROC_CMPT', '완료', 2),
    ('PAYROLL_STATUS', 'PDF_GEN', 'PDF생성', 3),
    ('PAYROLL_STATUS', 'MAIL_SENT', '발송완료', 4); 