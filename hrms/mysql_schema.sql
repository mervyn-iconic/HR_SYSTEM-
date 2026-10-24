-- MySQL 8.0.16+; select your empty hr_management database first.

CREATE TABLE department (
	department_id INTEGER NOT NULL AUTO_INCREMENT, 
	department_name VARCHAR(255) NOT NULL, 
	description VARCHAR(255), 
	location VARCHAR(255), 
	manager_id INTEGER, 
	PRIMARY KEY (department_id), 
	UNIQUE (department_name)
);

CREATE TABLE job (
	job_id INTEGER NOT NULL AUTO_INCREMENT, 
	job_title VARCHAR(255) NOT NULL, 
	description VARCHAR(255), 
	min_salary NUMERIC(12, 2), 
	max_salary NUMERIC(12, 2), 
	job_level VARCHAR(255), 
	PRIMARY KEY (job_id), 
	CHECK (min_salary IS NULL OR min_salary >= 0), 
	CHECK (max_salary IS NULL OR max_salary >= min_salary)
);

CREATE TABLE employee (
	employee_id INTEGER NOT NULL AUTO_INCREMENT, 
	first_name VARCHAR(255) NOT NULL, 
	last_name VARCHAR(255) NOT NULL, 
	email VARCHAR(255) NOT NULL, 
	phone VARCHAR(255), 
	address VARCHAR(255), 
	date_of_birth DATE, 
	gender VARCHAR(255), 
	hire_date DATE NOT NULL, 
	department_id INTEGER NOT NULL, 
	job_id INTEGER NOT NULL, 
	PRIMARY KEY (employee_id), 
	UNIQUE (email)
);

CREATE TABLE attendance (
	attendance_id INTEGER NOT NULL AUTO_INCREMENT, 
	employee_id INTEGER NOT NULL, 
	attendance_date DATE NOT NULL, 
	check_in_time TIME, 
	check_out_time TIME, 
	status VARCHAR(255) NOT NULL, 
	hours_worked NUMERIC(12, 2), 
	PRIMARY KEY (attendance_id), 
	UNIQUE (employee_id, attendance_date), 
	CHECK (hours_worked IS NULL OR hours_worked >= 0)
);

CREATE TABLE job_history (
	job_history_id INTEGER NOT NULL AUTO_INCREMENT, 
	employee_id INTEGER NOT NULL, 
	job_id INTEGER NOT NULL, 
	department_id INTEGER NOT NULL, 
	start_date DATE NOT NULL, 
	end_date DATE, 
	reason_for_change VARCHAR(255), 
	PRIMARY KEY (job_history_id), 
	CHECK (end_date IS NULL OR end_date >= start_date)
);

CREATE TABLE salary (
	salary_id INTEGER NOT NULL AUTO_INCREMENT, 
	employee_id INTEGER NOT NULL, 
	basic_salary NUMERIC(12, 2) NOT NULL, 
	effective_date DATE NOT NULL, 
	end_date DATE, 
	reason VARCHAR(255), 
	PRIMARY KEY (salary_id), 
	CHECK (basic_salary >= 0)
);

CREATE TABLE payroll (
	payroll_id INTEGER NOT NULL AUTO_INCREMENT, 
	employee_id INTEGER NOT NULL, 
	pay_period VARCHAR(255) NOT NULL, 
	basic_salary NUMERIC(12, 2) NOT NULL, 
	allowances NUMERIC(12, 2) NOT NULL DEFAULT '0', 
	deductions NUMERIC(12, 2) NOT NULL DEFAULT '0', 
	net_salary NUMERIC(12, 2) NOT NULL, 
	payment_date DATE, 
	payment_status VARCHAR(255) NOT NULL, 
	PRIMARY KEY (payroll_id), 
	UNIQUE (employee_id, pay_period), 
	CHECK (basic_salary >= 0 AND allowances >= 0 AND deductions >= 0 AND net_salary >= 0)
);

CREATE TABLE leave_type (
	leave_type_id INTEGER NOT NULL AUTO_INCREMENT, 
	leave_type_name VARCHAR(255) NOT NULL, 
	description VARCHAR(255), 
	max_days INTEGER NOT NULL, 
	PRIMARY KEY (leave_type_id), 
	CHECK (max_days >= 0), 
	UNIQUE (leave_type_name)
);

CREATE TABLE leave_request (
	leave_request_id INTEGER NOT NULL AUTO_INCREMENT, 
	employee_id INTEGER NOT NULL, 
	leave_type_id INTEGER NOT NULL, 
	start_date DATE NOT NULL, 
	end_date DATE NOT NULL, 
	reason VARCHAR(255), 
	status VARCHAR(255) NOT NULL, 
	approved_by INTEGER, 
	approval_date DATE, 
	PRIMARY KEY (leave_request_id), 
	CHECK (end_date IS NULL OR end_date >= start_date)
);

CREATE TABLE job_posting (
	job_posting_id INTEGER NOT NULL AUTO_INCREMENT, 
	job_id INTEGER NOT NULL, 
	department_id INTEGER NOT NULL, 
	title VARCHAR(255) NOT NULL, 
	description VARCHAR(255), 
	requirements VARCHAR(255), 
	posting_date DATE NOT NULL, 
	closing_date DATE, 
	number_of_positions INTEGER NOT NULL, 
	status VARCHAR(255) NOT NULL, 
	PRIMARY KEY (job_posting_id), 
	CHECK (number_of_positions > 0)
);

CREATE TABLE job_application (
	job_application_id INTEGER NOT NULL AUTO_INCREMENT, 
	posting_id INTEGER NOT NULL, 
	employee_id INTEGER NOT NULL, 
	application_date DATE NOT NULL, 
	status VARCHAR(255) NOT NULL, 
	cover_letter VARCHAR(255), 
	resume_path VARCHAR(255), 
	PRIMARY KEY (job_application_id)
);

CREATE TABLE performance_review (
	performance_review_id INTEGER NOT NULL AUTO_INCREMENT, 
	employee_id INTEGER NOT NULL, 
	review_date DATE NOT NULL, 
	review_period VARCHAR(255) NOT NULL, 
	overall_score NUMERIC(12, 2) NOT NULL, 
	comments VARCHAR(255), 
	reviewer_id INTEGER NOT NULL, 
	PRIMARY KEY (performance_review_id), 
	CHECK (overall_score >= 0 AND overall_score <= 5)
);

CREATE TABLE training (
	training_id INTEGER NOT NULL AUTO_INCREMENT, 
	training_name VARCHAR(255) NOT NULL, 
	description VARCHAR(255), 
	provider VARCHAR(255), 
	start_date DATE NOT NULL, 
	end_date DATE, 
	location VARCHAR(255), 
	goal VARCHAR(255), 
	PRIMARY KEY (training_id), 
	CHECK (end_date IS NULL OR end_date >= start_date)
);

CREATE TABLE employee_training (
	employee_training_id INTEGER NOT NULL AUTO_INCREMENT, 
	employee_id INTEGER NOT NULL, 
	training_id INTEGER NOT NULL, 
	registration_date DATE NOT NULL, 
	completion_date DATE, 
	status VARCHAR(255) NOT NULL, 
	result VARCHAR(255), 
	PRIMARY KEY (employee_training_id), 
	UNIQUE (employee_id, training_id)
);

CREATE TABLE benefit (
	benefit_id INTEGER NOT NULL AUTO_INCREMENT, 
	benefit_name VARCHAR(255) NOT NULL, 
	description VARCHAR(255), 
	amount NUMERIC(12, 2), 
	frequency VARCHAR(255), 
	PRIMARY KEY (benefit_id), 
	CHECK (amount IS NULL OR amount >= 0)
);

CREATE TABLE employment_benefit (
	employment_benefit_id INTEGER NOT NULL AUTO_INCREMENT, 
	employee_id INTEGER NOT NULL, 
	benefit_id INTEGER NOT NULL, 
	start_date DATE NOT NULL, 
	end_date DATE, 
	status VARCHAR(255) NOT NULL, 
	PRIMARY KEY (employment_benefit_id), 
	CHECK (end_date IS NULL OR end_date >= start_date)
);

ALTER TABLE department ADD CONSTRAINT department_fk_manager_id_employee FOREIGN KEY(manager_id) REFERENCES employee (employee_id) ON DELETE RESTRICT;

ALTER TABLE employee_training ADD CONSTRAINT employee_training_fk_training_id_training FOREIGN KEY(training_id) REFERENCES training (training_id) ON DELETE RESTRICT;

ALTER TABLE job_history ADD CONSTRAINT job_history_fk_employee_id_employee FOREIGN KEY(employee_id) REFERENCES employee (employee_id) ON DELETE RESTRICT;

ALTER TABLE performance_review ADD CONSTRAINT performance_review_fk_employee_id_employee FOREIGN KEY(employee_id) REFERENCES employee (employee_id) ON DELETE RESTRICT;

ALTER TABLE employment_benefit ADD CONSTRAINT employment_benefit_fk_employee_id_employee FOREIGN KEY(employee_id) REFERENCES employee (employee_id) ON DELETE RESTRICT;

ALTER TABLE attendance ADD CONSTRAINT attendance_fk_employee_id_employee FOREIGN KEY(employee_id) REFERENCES employee (employee_id) ON DELETE RESTRICT;

ALTER TABLE job_history ADD CONSTRAINT job_history_fk_job_id_job FOREIGN KEY(job_id) REFERENCES job (job_id) ON DELETE RESTRICT;

ALTER TABLE employee ADD CONSTRAINT employee_fk_department_id_department FOREIGN KEY(department_id) REFERENCES department (department_id) ON DELETE RESTRICT;

ALTER TABLE leave_request ADD CONSTRAINT leave_request_fk_employee_id_employee FOREIGN KEY(employee_id) REFERENCES employee (employee_id) ON DELETE RESTRICT;

ALTER TABLE employment_benefit ADD CONSTRAINT employment_benefit_fk_benefit_id_benefit FOREIGN KEY(benefit_id) REFERENCES benefit (benefit_id) ON DELETE RESTRICT;

ALTER TABLE job_history ADD CONSTRAINT job_history_fk_department_id_department FOREIGN KEY(department_id) REFERENCES department (department_id) ON DELETE RESTRICT;

ALTER TABLE job_application ADD CONSTRAINT job_application_fk_posting_id_job_posting FOREIGN KEY(posting_id) REFERENCES job_posting (job_posting_id) ON DELETE RESTRICT;

ALTER TABLE performance_review ADD CONSTRAINT performance_review_fk_reviewer_id_employee FOREIGN KEY(reviewer_id) REFERENCES employee (employee_id) ON DELETE RESTRICT;

ALTER TABLE leave_request ADD CONSTRAINT leave_request_fk_leave_type_id_leave_type FOREIGN KEY(leave_type_id) REFERENCES leave_type (leave_type_id) ON DELETE RESTRICT;

ALTER TABLE job_posting ADD CONSTRAINT job_posting_fk_job_id_job FOREIGN KEY(job_id) REFERENCES job (job_id) ON DELETE RESTRICT;

ALTER TABLE job_application ADD CONSTRAINT job_application_fk_employee_id_employee FOREIGN KEY(employee_id) REFERENCES employee (employee_id) ON DELETE RESTRICT;

ALTER TABLE leave_request ADD CONSTRAINT leave_request_fk_approved_by_employee FOREIGN KEY(approved_by) REFERENCES employee (employee_id) ON DELETE RESTRICT;

ALTER TABLE job_posting ADD CONSTRAINT job_posting_fk_department_id_department FOREIGN KEY(department_id) REFERENCES department (department_id) ON DELETE RESTRICT;

ALTER TABLE employee ADD CONSTRAINT employee_fk_job_id_job FOREIGN KEY(job_id) REFERENCES job (job_id) ON DELETE RESTRICT;

ALTER TABLE payroll ADD CONSTRAINT payroll_fk_employee_id_employee FOREIGN KEY(employee_id) REFERENCES employee (employee_id) ON DELETE RESTRICT;

ALTER TABLE employee_training ADD CONSTRAINT employee_training_fk_employee_id_employee FOREIGN KEY(employee_id) REFERENCES employee (employee_id) ON DELETE RESTRICT;

ALTER TABLE salary ADD CONSTRAINT salary_fk_employee_id_employee FOREIGN KEY(employee_id) REFERENCES employee (employee_id) ON DELETE RESTRICT;
