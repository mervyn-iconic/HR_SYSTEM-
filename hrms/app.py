import os, secrets, csv, io
from datetime import date, time, timedelta
from time import monotonic
from threading import Lock
from decimal import Decimal
from functools import wraps
from pathlib import Path
from flask import Flask, request, jsonify, session, render_template, Response, send_file
from sqlalchemy import create_engine, event, select, func
from sqlalchemy.exc import IntegrityError, StatementError
from werkzeug.security import check_password_hash, generate_password_hash
from schema import metadata, tables
app=Flask(__name__)
app.secret_key=os.environ.get('SECRET_KEY') or secrets.token_hex(32)
app.config.update(SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SAMESITE='Strict',MAX_CONTENT_LENGTH=1024*1024)
app.config['PERMANENT_SESSION_LIFETIME']=timedelta(hours=8)
login_attempts=[]
login_lock=Lock()
STATUS_OPTIONS={
 'attendance':{'status':['Present','Absent','Late','On leave']},
 'leave_request':{'status':['Pending','Approved','Rejected','Cancelled']},
 'payroll':{'payment_status':['Pending','Paid','Cancelled']},
 'job_posting':{'status':['Draft','Open','Closed']},
 'job_application':{'status':['Submitted','Shortlisted','Interview','Offered','Rejected','Withdrawn']},
 'employee_training':{'status':['Registered','In progress','Completed','Cancelled']},
 'employment_benefit':{'status':['Active','Inactive']}
}
engine=create_engine(os.environ.get('DATABASE_URL','sqlite:///'+str(Path(__file__).with_name('hrms.db'))))
if engine.dialect.name=='sqlite':
    @event.listens_for(engine,'connect')
    def enforce(dbapi, _): dbapi.execute('PRAGMA foreign_keys=ON')
metadata.create_all(engine)
ADMIN_HASH=generate_password_hash(os.environ.get('HR_ADMIN_PASSWORD') or secrets.token_urlsafe(18))
if not os.environ.get('HR_ADMIN_PASSWORD'):
    print('Set HR_ADMIN_PASSWORD before starting to choose your login password. Current login is disabled.')
def auth(fn):
    @wraps(fn)
    def wrapped(*a,**kw):
        if not session.get('admin'): return jsonify(error='Please sign in.'),401
        if request.method not in ('GET','HEAD') and request.headers.get('X-CSRF-Token')!=session.get('csrf'): return jsonify(error='Session token expired. Refresh the page.'),403
        return fn(*a,**kw)
    return wrapped
@app.get('/company-logo')
def company_logo():
    # Use the original company artwork wherever it is installed.
    static=Path(app.static_folder)
    for filename in ('company-logo.png','company-logo.jpg','company-logo.jpeg','company-logo.webp'):
        path=static/filename
        if path.is_file(): return send_file(path,max_age=0)
    return send_file(static/'golden-marketing.svg',max_age=0)
@app.after_request
def refresh_ui_assets(response):
    if request.path in ('/', '/company-logo', '/static/app.js', '/static/style.css'):
        response.headers['Cache-Control']='no-store'
    return response
@app.get('/')
def index(): return render_template('index.html')
@app.post('/api/login')
def login():
    data=request.get_json(silent=True) or {}
    if not isinstance(data,dict) or not isinstance(data.get('password'),str): return jsonify(error='Enter your administrator password.'),400
    with login_lock:
        now=monotonic()
        login_attempts[:]=[t for t in login_attempts if now-t<60]
        if len(login_attempts)>=10: return jsonify(error='Too many sign-in attempts. Wait one minute and try again.'),429
        login_attempts.append(now)
    if not check_password_hash(ADMIN_HASH,data['password']): return jsonify(error='Incorrect password.'),401
    session.clear();session.permanent=True;session.update(admin=True,csrf=secrets.token_hex(24))
    return jsonify(csrf=session['csrf'])
@app.get('/api/session')
@auth
def current(): return jsonify(csrf=session['csrf'])
@app.post('/api/logout')
@auth
def logout(): session.clear(); return jsonify(ok=True)
@app.get('/api/schema')
@auth
def schema():
    return jsonify({name:[dict(name=c.name,type=str(c.type),required=not c.nullable and not c.primary_key and c.server_default is None,primary=c.primary_key,options=STATUS_OPTIONS.get(name,{}).get(c.name),reference=next(iter(c.foreign_keys)).column.table.name if c.foreign_keys else None) for c in t.c] for name,t in tables.items()})
def serialize(row): return {k:str(v) if isinstance(v,(date,time,Decimal)) else v for k,v in row.items()}
def get_table(name):
    if name not in tables: raise ValueError('Unknown table')
    return tables[name]
@app.route('/api/records/<name>',methods=['GET','POST'])
@app.route('/api/records/<name>/<int:record_id>',methods=['PUT','DELETE'])
@auth
def records(name,record_id=None):
    try:
        t=get_table(name);pk=list(t.primary_key)[0]
        with engine.begin() as conn:
            if request.method=='GET':
                rows=[serialize(r) for r in conn.execute(select(t).order_by(pk.desc())).mappings()]
                if request.args.get('format')=='csv':
                    out=io.StringIO();w=csv.DictWriter(out,fieldnames=[c.name for c in t.c]);w.writeheader()
                    for r in rows:
                        w.writerow({k:("'"+v if isinstance(v,str) and v.startswith(('=','+','-','@','\t','\r')) else v) for k,v in r.items()})
                    return Response(out.getvalue(),mimetype='text/csv',headers={'Content-Disposition':f'attachment; filename={name}.csv'})
                return jsonify(rows)
            if record_id is not None and conn.execute(select(pk).where(pk==record_id)).first() is None: return jsonify(error='Record not found.'),404
            if request.method=='DELETE': conn.execute(t.delete().where(pk==record_id));return jsonify(ok=True)
            data=request.get_json(silent=True) or {}; values={}
            if not isinstance(data,dict): raise ValueError('Provide a record object.')
            for key,value in data.items():
                if key not in t.c or t.c[key].primary_key: raise ValueError('Unknown or read-only field: '+key)
                c=t.c[key]
                if value in ('',None): value=None
                elif str(c.type)=='DATE': value=date.fromisoformat(value)
                elif str(c.type)=='TIME': value=time.fromisoformat(value)
                elif str(c.type)=='INTEGER': value=int(value)
                elif str(c.type).startswith('NUMERIC'): value=Decimal(str(value))
                else:
                    value=str(value).strip()
                    if len(value)>255: raise ValueError(key+' must be at most 255 characters.')
                if not c.nullable and not c.primary_key and value is None:
                    if c.server_default is not None: value=Decimal('0')
                    else: raise ValueError(key.replace('_',' ')+' is required.')
                if isinstance(value,str) and not value and not c.nullable: raise ValueError(key+' cannot be blank.')
                if isinstance(value,Decimal) and not value.is_finite(): raise ValueError(key+' must be a finite number.')
                options=STATUS_OPTIONS.get(name,{}).get(key)
                if options and value not in options: raise ValueError('Choose a valid '+key+'.')
                values[key]=value
            if name=='employee' and 'email' in values and ('@' not in (values['email'] or '')): raise ValueError('Enter a valid email address.')
            if name=='payroll':
                merged=dict(conn.execute(select(t).where(pk==record_id)).mappings().first() or {}) if record_id else {}
                merged.update(values)
                values['net_salary']=Decimal(str(merged.get('basic_salary') or 0))+Decimal(str(merged.get('allowances') or 0))-Decimal(str(merged.get('deductions') or 0))
            if request.method=='POST':
                result=conn.execute(t.insert().values(**values)); record_id=result.inserted_primary_key[0]
            else: conn.execute(t.update().where(pk==record_id).values(**values))
            return jsonify(id=record_id)
    except IntegrityError: return jsonify(error='This change violates a required field, unique value, date/range rule, or linked record. Remove dependent records before deleting.'),400
    except (ValueError,StatementError,TypeError,ArithmeticError) as e: return jsonify(error='Invalid input: '+str(e).split('\n')[0]),400
@app.get('/api/summary')
@auth
def summary():
    with engine.connect() as c:
        counts={n:c.scalar(select(func.count()).select_from(t)) for n,t in tables.items()}
        counts['pending_leave']=c.scalar(select(func.count()).select_from(tables['leave_request']).where(tables['leave_request'].c.status=='Pending'))
        counts['departments']=[dict(r) for r in c.execute(select(tables['department'].c.department_name,func.count(tables['employee'].c.employee_id).label('count')).select_from(tables['department'].outerjoin(tables['employee'],tables['employee'].c.department_id==tables['department'].c.department_id)).group_by(tables['department'].c.department_id,tables['department'].c.department_name)).mappings()]
    return jsonify(counts)
@app.after_request
def headers(response):
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['X-Frame-Options']='DENY'
    response.headers['Content-Security-Policy']="default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; object-src 'none'; frame-ancestors 'none'"
    response.headers['Cache-Control']='no-store'
    return response
if __name__=='__main__': app.run(host='127.0.0.1',port=int(os.environ.get('PORT',5000)),debug=False)
