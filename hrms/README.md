# HR Management System

Flask + SQLAlchemy application based on the supplied HR Management System ERD and Database Report. The existing Django starter in the repository root is preserved; this application is independent.

## Easiest Windows startup

1. Extract the downloaded repository ZIP.
2. Open `hrms` and double-click **start_windows.bat**.
3. The launcher creates its own environment, installs dependencies, and asks you to choose and confirm an administrator password of at least 12 characters. Password input is hidden while typing.
4. Your browser opens once the server is ready. Sign in with that password and keep the launcher window open.

Python 3.12+ must be installed with **Add Python to PATH** enabled. First-time setup requires internet access to install dependencies. If a password is already configured in the environment, the launcher uses it. Without that configuration, choose a password each time you launch; it is not saved to disk. Your HR records persist in `hrms.db` independently of the login password.

**Updating an existing installation:** stop the app with Ctrl+C and back up `hrms.db` first. Copy the new `hrms` folder contents into your existing `hrms` folder, keeping `hrms.db`, then run `start_windows.bat`. Downloaded source does not include your database. Do not delete your old folder before backing it up.

## Start locally

Python 3.12+ recommended. Run in this folder:

```sh
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell instead: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Choose a strong password and session secret in your shell (do not commit them):

```sh
export HR_ADMIN_PASSWORD='your-chosen-password'
export SECRET_KEY='your-long-random-secret'
python app.py
```

PowerShell uses `$env:HR_ADMIN_PASSWORD='your-chosen-password'` and `$env:SECRET_KEY='your-long-random-secret'`.
Open **http://127.0.0.1:5000** and sign in with the chosen password. Set `PORT` to change the port. No password is committed. If no password is configured, sign-in is disabled. The default SQLite file is created automatically and starts empty. Set up departments and jobs first, employees next, then dependent records. Set department managers after creating employees.

## MySQL / MySQL Workbench

Create a database with MySQL Workbench or the MySQL CLI:

```sql
CREATE DATABASE hr_management CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Configure an application database user with access to that database, then set:

```sh
export DATABASE_URL='mysql+pymysql://USER:PASSWORD@127.0.0.1:3306/hr_management'
python app.py
```

URL-encode special characters in credentials. Tables are created on first start. MySQL 8.0.16+ is required to enforce CHECK constraints. `mysql_schema.sql` is a Workbench-compatible alternative to automatic creation. Do not import it into an already initialized database. SQLite is the tested local preview; MySQL requires your running MySQL server and credentials. Back up databases before schema changes; automatic creation does not migrate existing tables.

## Features

- Authenticated administrator interface; create, read, update, delete, search and CSV export for all 16 ERD tables.
- Dashboard with actual employee counts, department distribution and pending leave requests.
- Primary keys, foreign keys, unique email, one attendance record per employee/day, one payroll per employee/period, and training enrollment uniqueness.
- Payroll net salary computed from basic salary + allowances − deductions. Amounts use decimal storage. No currency or tax rules are assumed.
- Date range checks, nonnegative salaries and benefits, and performance scores on an explicitly assumed 0–5 scale.
- CSRF protection, escaped UI data, restricted local binding, authenticated exports and CSV formula protection.

## Design notes

The 16 business tables mirror the diagram, including its internal recruitment model: job applications reference an existing employee. External applicant recruitment would require an additional applicant entity. The ERD's `posting_id` references `job_posting.job_posting_id`; `approved_by` and `reviewer_id` reference employees. Department-to-manager is nullable to resolve the employee/department creation cycle. Foreign-key deletion is restricted to preserve history. Report statements about prior implementation/testing are source claims, not verification of this build.

This is a local administrator application. Role-based employee accounts, leave allowance policy enforcement, automatic attendance hours, audit logs, file uploads, payroll tax calculations and production hosting are not implemented. Resume paths are text references, not file uploads. Review these requirements before organizational deployment. List endpoints currently load full tables and should be paginated for larger organizations.

## Verification

```sh
python -m unittest discover -s tests -v
```

Tests use an isolated temporary SQLite database, and cover authentication, CSRF, all-table reads, CRUD, linked-record protection, duplicate emails, date constraints, payroll calculation and CSV export. MySQL DDL is compiled but a live MySQL integration test requires a server.

## PeopleDesk interface improvements

The refreshed interface includes readable linked employee/department/job names, status badges and filters, 12-record pages, searchable linked names, setup shortcuts and responsive layouts. Status choices are validated by the API; legacy free-text statuses should be changed to a listed choice when editing. Empty optional payroll amounts default to zero. Sessions expire after eight hours and login attempts are limited to ten per minute per running process. This limit is intended for local use; shared deployment needs a persistent rate limiter.

Verification includes API tests and a DOM integration exercise against the running server for sign-in, navigation and forms. A full browser visual review and execution of the Windows batch launcher on Windows were not available in the build environment.
