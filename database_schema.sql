-- 사용자 테이블
CREATE TABLE user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT,
    email TEXT UNIQUE,
    is_active INTEGER DEFAULT 1,
    is_admin INTEGER DEFAULT 0,
    last_login DATETIME,
    login_ip TEXT,
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until DATETIME,
    created_at DATETIME DEFAULT (datetime('now', 'localtime')),
    updated_at DATETIME
);

-- 직원 테이블
CREATE TABLE employee (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    emp_number TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    birth_date DATE,
    join_date DATE,
    position TEXT,
    email TEXT UNIQUE,
    pdf_password TEXT,
    created_at DATETIME DEFAULT (datetime('now', 'localtime')),
    created_by TEXT,
    created_ip TEXT,
    updated_at DATETIME,
    updated_by TEXT,
    updated_ip TEXT
);

-- 직원 이력 테이블
CREATE TABLE employee_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL,
    field_name TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    changed_by TEXT,
    changed_at DATETIME DEFAULT (datetime('now', 'localtime')),
    changed_ip TEXT,
    FOREIGN KEY (employee_id) REFERENCES employee(id)
);

-- 급여 테이블
CREATE TABLE salary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    emp_id INTEGER NOT NULL,
    payment_date DATE NOT NULL,
    base_salary INTEGER,
    position_bonus INTEGER,
    overtime_pay INTEGER,
    meal_allowance INTEGER,
    FOREIGN KEY (emp_id) REFERENCES employee(id)
);

-- 급여 기록 테이블
CREATE TABLE payroll_record (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pay_year_month TEXT NOT NULL,  -- YYYY-MM 형식
    payment_date DATE NOT NULL,
    status TEXT DEFAULT '임시저장',
    created_at DATETIME DEFAULT (datetime('now', 'localtime')),
    created_by TEXT,
    created_ip TEXT,
    updated_at DATETIME,
    updated_by TEXT,
    updated_ip TEXT
);

-- 급여 상세 테이블
CREATE TABLE payroll_detail (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id INTEGER NOT NULL,
    employee_id TEXT NOT NULL,
    employee_name TEXT NOT NULL,
    department TEXT,
    position TEXT,
    base_salary INTEGER DEFAULT 0,
    position_allowance INTEGER DEFAULT 0,
    meal_allowance INTEGER DEFAULT 0,
    car_allowance INTEGER DEFAULT 0,
    total_payment INTEGER DEFAULT 0,
    income_tax INTEGER DEFAULT 0,
    local_income_tax INTEGER DEFAULT 0,
    national_pension INTEGER DEFAULT 0,
    health_insurance INTEGER DEFAULT 0,
    long_term_care INTEGER DEFAULT 0,
    employment_insurance INTEGER DEFAULT 0,
    total_deduction INTEGER DEFAULT 0,
    net_amount INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (record_id) REFERENCES payroll_record(id)
);

-- 인덱스 생성
CREATE INDEX idx_user_username ON user(username);
CREATE INDEX idx_user_email ON user(email);
CREATE INDEX idx_user_last_login ON user(last_login);

CREATE INDEX idx_employee_emp_number ON employee(emp_number);
CREATE INDEX idx_employee_email ON employee(email);
CREATE INDEX idx_employee_position ON employee(position);
CREATE INDEX idx_employee_join_date ON employee(join_date);

CREATE INDEX idx_employee_history_employee_id ON employee_history(employee_id);
CREATE INDEX idx_employee_history_changed_at ON employee_history(changed_at);

CREATE INDEX idx_salary_emp_id ON salary(emp_id);
CREATE INDEX idx_salary_payment_date ON salary(payment_date);

CREATE INDEX idx_payroll_record_pay_year_month ON payroll_record(pay_year_month);
CREATE INDEX idx_payroll_record_payment_date ON payroll_record(payment_date);

CREATE INDEX idx_payroll_detail_record_id ON payroll_detail(record_id);
CREATE INDEX idx_payroll_detail_employee_id ON payroll_detail(employee_id);

-- 뷰 생성 (급여 통계용)
CREATE VIEW v_payroll_summary AS
SELECT 
    pr.pay_year_month,
    pr.payment_date,
    COUNT(pd.id) as employee_count,
    SUM(pd.total_payment) as total_payment_amount,
    SUM(pd.total_deduction) as total_deduction_amount,
    SUM(pd.net_amount) as total_net_amount,
    pr.status
FROM payroll_record pr
LEFT JOIN payroll_detail pd ON pr.id = pd.record_id
GROUP BY pr.id, pr.pay_year_month, pr.payment_date, pr.status; 