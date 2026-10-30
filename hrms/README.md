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

## Golden Marketing interface improvements

The refreshed interface includes readable linked employee/department/job names, status badges and filters, 12-record pages, searchable linked names, setup shortcuts and responsive layouts. Status choices are validated by the API; legacy free-text statuses should be changed to a listed choice when editing. Empty optional payroll amounts default to zero. Sessions expire after eight hours and login attempts are limited to ten per minute per running process. This limit is intended for local use; shared deployment needs a persistent rate limiter.

Verification includes API tests and a DOM integration exercise against the running server for sign-in, navigation and forms. A full browser visual review and execution of the Windows batch launcher on Windows were not available in the build environment.

## Company branding

Golden Marketing branding uses approximate colors sampled visually from the supplied references: navy `#201f30`, gold `#b89222`, ivory `#faf9f6`, and muted purple `#62618a`. The local SVG wordmark is a vector recreation from the screenshot, not the original company master artwork. Replace `static/golden-marketing.svg` with the official artwork when available, retaining the same filename or updating the two image references in the template. Branding changes do not change the database schema or employee records.

### Install the exact company logo

Save the original supplied company image as `hrms/static/company-logo.png` (a genuine PNG file), or `company-logo.jpg`, `company-logo.jpeg`, or `company-logo.webp` matching the actual file format. The app automatically serves that original file at `/company-logo` for the login page, sidebar, all page headers, record dialogs and browser icon. No source editing is needed; refresh the browser after replacing it. Until an original image file is installed, the existing recreated SVG remains the fallback. No original image was available as a downloadable attachment in the build workspace.

### Apply code and original logo together on Windows

Stop the running app, save the original company logo image on your computer, and run `scripts/Update-GoldenMarketing.ps1` with Windows PowerShell. It defaults to `D:\HR_SYSTEM--Main\hrms`; override with `-InstallPath` if needed. A file picker asks for the original logo. The updater stages the download, backs up the existing code and database to a sibling folder, installs the latest code without replacing the database or `.env`, selects the supplied image as the shared logo, and launches the application. Cancelling the file picker leaves the installation unchanged. The updater requires internet access and has not been executed on Windows in the build environment.

## Bulk CSV tools

Every subsection has **Import CSV** and **Export all records**. The page header also has **Export all sections**, which downloads a ZIP with all 16 CSV tables. Exports include every record, regardless of the current search or page.

For imports, download the subsection template, fill in one new record per row, then select **Validate file** and **Import records**. Files are UTF-8 CSV, at most 500 KB and 5,000 records. You may upload the exported CSV including its primary ID column. Matching IDs update existing records; new IDs are preserved when creating records, and blank or omitted IDs are generated automatically. Use existing numeric IDs in linked columns; the import dialog links to those sections' CSV exports. Create departments and jobs before employees, then attendance, payroll and other dependent records. Payroll net salary is calculated automatically. Review the new/update counts before confirming. Rows without matching IDs create new records. Any failed row rejects the entire file, with its row number shown. Validation saves nothing. Use Overview → Import all sections to import an all-section export ZIP.

## Import all sections from Overview

Upload the ZIP produced by **Export all sections** (10 MB maximum, 20 MB uncompressed, 5,000 rows per table and 20,000 total). All 16 CSV files must be present at the top level with unchanged headers, including primary IDs. Validate first to inspect new/update counts per section, then confirm. Matching primary IDs update records; other IDs create records. Records absent from the ZIP are retained. Keep linked IDs consistent; department managers are applied after employees to handle that circular relationship. Any validation or database failure rolls back the entire import. This restores record data, not account settings or uploaded files.

### Date formats in imports

Date fields accept `YYYY-MM-DD`, `DD/MM/YYYY` and `DD-MM-YYYY`, including surrounding whitespace. Slash and day-first hyphen formats always mean day/month/year: `01/02/2026` means 1 February. Invalid calendar dates are rejected with the field name and CSV row; the entire file is rolled back. This applies to per-section CSV and Overview ZIP imports.
