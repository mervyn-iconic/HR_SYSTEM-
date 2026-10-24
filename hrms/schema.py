from sqlalchemy import *
metadata = MetaData()
tables = {}
def table(name, *columns, constraints=()):
    tables[name] = Table(name, metadata, Column(name+'_id', Integer, primary_key=True), *columns, *constraints)
    for constraint in tables[name].foreign_key_constraints:
        constraint.name = name + '_' + constraint.name
def s(name, required=False, unique=False): return Column(name, String(255), nullable=not required, unique=unique)
def d(name, required=False): return Column(name, Date, nullable=not required)
def n(name, required=False): return Column(name, Numeric(12,2), nullable=not required)
def fk(name, target, required=False): return Column(name, Integer, ForeignKey(target+'.'+target+'_id', ondelete='RESTRICT', use_alter=True, name='fk_'+name+'_'+target), nullable=not required)
table('department',s('department_name',True,True),s('description'),s('location'),fk('manager_id','employee'))
table('job',s('job_title',True),s('description'),n('min_salary'),n('max_salary'),s('job_level'),constraints=(CheckConstraint('min_salary IS NULL OR min_salary >= 0'),CheckConstraint('max_salary IS NULL OR max_salary >= min_salary')))
table('employee',s('first_name',True),s('last_name',True),s('email',True,True),s('phone'),s('address'),d('date_of_birth'),s('gender'),d('hire_date',True),fk('department_id','department',True),fk('job_id','job',True))
table('attendance',fk('employee_id','employee',True),d('attendance_date',True),Column('check_in_time',Time),Column('check_out_time',Time),s('status',True),n('hours_worked'),constraints=(UniqueConstraint('employee_id','attendance_date'),CheckConstraint('hours_worked IS NULL OR hours_worked >= 0')))
table('job_history',fk('employee_id','employee',True),fk('job_id','job',True),fk('department_id','department',True),d('start_date',True),d('end_date'),s('reason_for_change'))
table('salary',fk('employee_id','employee',True),n('basic_salary',True),d('effective_date',True),d('end_date'),s('reason'),constraints=(CheckConstraint('basic_salary >= 0'),))
table('payroll',fk('employee_id','employee',True),s('pay_period',True),n('basic_salary',True),Column('allowances',Numeric(12,2),nullable=False,server_default='0'),Column('deductions',Numeric(12,2),nullable=False,server_default='0'),n('net_salary',True),d('payment_date'),s('payment_status',True),constraints=(UniqueConstraint('employee_id','pay_period'),CheckConstraint('basic_salary >= 0 AND allowances >= 0 AND deductions >= 0 AND net_salary >= 0')))
table('leave_type',s('leave_type_name',True,True),s('description'),Column('max_days',Integer,nullable=False),constraints=(CheckConstraint('max_days >= 0'),))
table('leave_request',fk('employee_id','employee',True),fk('leave_type_id','leave_type',True),d('start_date',True),d('end_date',True),s('reason'),s('status',True),fk('approved_by','employee'),d('approval_date'))
table('job_posting',fk('job_id','job',True),fk('department_id','department',True),s('title',True),s('description'),s('requirements'),d('posting_date',True),d('closing_date'),Column('number_of_positions',Integer,nullable=False),s('status',True),constraints=(CheckConstraint('number_of_positions > 0'),))
table('job_application',fk('posting_id','job_posting',True),fk('employee_id','employee',True),d('application_date',True),s('status',True),s('cover_letter'),s('resume_path'))
table('performance_review',fk('employee_id','employee',True),d('review_date',True),s('review_period',True),n('overall_score',True),s('comments'),fk('reviewer_id','employee',True),constraints=(CheckConstraint('overall_score >= 0 AND overall_score <= 5'),))
table('training',s('training_name',True),s('description'),s('provider'),d('start_date',True),d('end_date'),s('location'),s('goal'))
table('employee_training',fk('employee_id','employee',True),fk('training_id','training',True),d('registration_date',True),d('completion_date'),s('status',True),s('result'),constraints=(UniqueConstraint('employee_id','training_id'),))
table('benefit',s('benefit_name',True),s('description'),n('amount'),s('frequency'),constraints=(CheckConstraint('amount IS NULL OR amount >= 0'),))
table('employment_benefit',fk('employee_id','employee',True),fk('benefit_id','benefit',True),d('start_date',True),d('end_date'),s('status',True))
for name,t in tables.items():
    if 'start_date' in t.c and 'end_date' in t.c:
        t.append_constraint(CheckConstraint('end_date IS NULL OR end_date >= start_date'))
