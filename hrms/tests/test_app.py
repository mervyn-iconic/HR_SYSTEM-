import os,tempfile,unittest
_tmp=tempfile.TemporaryDirectory()
os.environ['DATABASE_URL']='sqlite:///'+_tmp.name+'/test.db'
os.environ['HR_ADMIN_PASSWORD']='test-only-password'
from app import app,metadata,engine
class HRTests(unittest.TestCase):
    def setUp(self):
        with engine.begin() as c:
            c.execute(metadata.tables['department'].update().values(manager_id=None))
            for t in reversed(list(metadata.tables.values())):c.execute(t.delete())
        self.c=app.test_client()
        self.token=self.c.post('/api/login',json={'password':'test-only-password'}).json['csrf']
    def post(self,t,d):return self.c.post('/api/records/'+t,json=d,headers={'X-CSRF-Token':self.token})
    def employee(self):
        dep=self.post('department',{'department_name':'Engineering'}).json['id']
        job=self.post('job',{'job_title':'Engineer'}).json['id']
        d={'first_name':'Test','last_name':'Person','email':'test@example.com','hire_date':'2026-01-01','department_id':dep,'job_id':job}
        return self.post('employee',d).json['id'],dep,d
    def test_auth_and_schema(self):
        self.assertEqual(app.test_client().get('/api/schema').status_code,401)
        self.assertEqual(len(self.c.get('/api/schema').json),16)
        self.assertEqual(self.c.post('/api/records/job',json={'job_title':'a'}).status_code,403)
        for name in metadata.tables:self.assertEqual(self.c.get('/api/records/'+name).status_code,200)
    def test_integrity_crud_and_export(self):
        emp,dep,d=self.employee()
        self.assertEqual(self.post('employee',d).status_code,400)
        r=self.c.delete('/api/records/department/'+str(dep),headers={'X-CSRF-Token':self.token})
        self.assertEqual(r.status_code,400)
        self.assertEqual(self.c.put('/api/records/employee/'+str(emp),json={'phone':'123'},headers={'X-CSRF-Token':self.token}).status_code,200)
        self.assertIn('test@example.com',self.c.get('/api/records/employee?format=csv').text)
        self.assertEqual(self.c.get('/api/summary').json['employee'],1)
    def test_validation_and_status_choices(self):
        schema=self.c.get('/api/schema').json
        self.assertIn('Approved',schema['leave_request'][6]['options'])
        self.assertEqual(self.post('department',{'department_name':'   '}).status_code,400)
        emp,_,_=self.employee()
        self.assertEqual(self.post('attendance',{'employee_id':emp,'attendance_date':'2026-10-24','status':'Made up'}).status_code,400)
        self.assertEqual(self.post('payroll',{'employee_id':emp,'pay_period':'2026-10','basic_salary':'1000','allowances':'','deductions':'','payment_status':'Pending'}).status_code,200)
        self.assertEqual(self.c.get('/api/records/payroll').json[0]['net_salary'],'1000.00')
        self.assertEqual(self.post('benefit',{'benefit_name':'Invalid','amount':'NaN'}).status_code,400)
    def test_login_throttle_and_logout(self):
        from app import login_attempts
        login_attempts.clear()
        for _ in range(10):
            self.assertEqual(self.c.post('/api/login',json={'password':'wrong'}).status_code,401)
        self.assertEqual(self.c.post('/api/login',json={'password':'wrong'}).status_code,429)
        login_attempts.clear()
        self.assertEqual(self.c.post('/api/logout',headers={'X-CSRF-Token':self.token}).status_code,200)
        self.assertEqual(self.c.get('/api/records/employee').status_code,401)
    def test_payroll_and_dates(self):
        emp,_,_=self.employee()
        self.assertEqual(self.post('payroll',{'employee_id':emp,'pay_period':'2026-10','basic_salary':'1000','allowances':'100','deductions':'50','net_salary':'9999','payment_status':'Pending'}).status_code,200)
        self.assertEqual(self.c.get('/api/records/payroll').json[0]['net_salary'],'1050.00')
        self.assertEqual(self.post('training',{'training_name':'Bad dates','start_date':'2026-10-20','end_date':'2026-10-01'}).status_code,400)
        self.assertEqual(self.post('attendance',{'employee_id':9999,'attendance_date':'2026-10-24','status':'Present'}).status_code,400)
    def bulk(self,name,text,dry_run=True):
        return self.c.post('/api/import/'+name,json={'csv':text,'dry_run':dry_run},headers={'X-CSRF-Token':self.token})
    def test_bulk_preview_commit_and_atomic_failure(self):
        text='department_name,description\nFinance,First\nOperations,Second\n'
        self.assertEqual(self.bulk('department',text).json['count'],2)
        self.assertEqual(self.c.get('/api/summary').json['department'],0)
        self.assertEqual(self.bulk('department',text,False).json['count'],2)
        self.assertEqual(self.c.get('/api/summary').json['department'],2)
        bad='department_name\nNew team\nFinance\n'
        result=self.bulk('department',bad,False)
        self.assertEqual(result.status_code,400)
        self.assertIn('row 3',result.json['error'])
        self.assertEqual(self.c.get('/api/summary').json['department'],2)
    def test_bulk_validation_and_permissions(self):
        self.assertEqual(app.test_client().post('/api/import/job',json={'csv':'job_title\nA'}).status_code,401)
        self.assertEqual(self.c.post('/api/import/job',json={'csv':'job_title\nA'}).status_code,403)
        for text in ['description\nMissing name','job_title,job_title\nA,B','job_id,job_title\n-1,A','job_title,description\nA,B,C']:
            self.assertEqual(self.bulk('job',text,False).status_code,400)
        bad='employee_id,attendance_date,status\n9999,2026-10-30,Present'
        self.assertEqual(self.bulk('attendance',bad,False).status_code,400)
        self.assertEqual(self.c.get('/api/summary').json['job'],0)
    def test_bulk_payroll_and_all_templates_exports(self):
        import zipfile,io
        emp,_,_=self.employee()
        text=f'employee_id,pay_period,basic_salary,allowances,deductions,payment_status\n{emp},2026-11,1000,100,50,Pending'
        self.assertEqual(self.bulk('payroll',text,False).status_code,200)
        self.assertEqual(self.c.get('/api/records/payroll').json[0]['net_salary'],'1050.00')
        for name in metadata.tables:
            response=self.c.get('/api/import/'+name+'/template')
            self.assertEqual(response.status_code,200)
            self.assertNotIn(name+'_id',response.text.split(',')[0])
        archive=zipfile.ZipFile(io.BytesIO(self.c.get('/api/export-all').data))
        self.assertEqual(len([n for n in archive.namelist() if n.endswith('.csv')]),16)
        self.assertIn('test@example.com',archive.read('employee.csv').decode('utf-8-sig'))
        self.assertEqual(self.bulk('job','job_title,description\n"Example, quoted","Two lines\nare valid"',False).status_code,200)
    def test_section_export_csv_reimport_ids(self):
        emp,_,_=self.employee()
        text=self.c.get('/api/records/employee?format=csv').text.replace('Test,Person','Updated,Person')
        preview=self.bulk('employee',text)
        self.assertEqual(preview.status_code,200,preview.json)
        self.assertEqual(preview.json['updated'],1)
        self.assertEqual(self.c.get('/api/records/employee').json[0]['first_name'],'Test')
        result=self.bulk('employee',text,False)
        self.assertEqual(result.status_code,200,result.json)
        self.assertEqual(result.json['created'],0)
        self.assertEqual(self.c.get('/api/records/employee').json[0]['first_name'],'Updated')
        self.assertEqual(self.c.get('/api/summary').json['employee'],1)
        self.assertEqual(self.bulk('job','job_id,job_title\n100,New job',False).json['created'],1)
        self.assertEqual(self.bulk('job','job_id,job_title\n,Generated ID',False).json['created'],1)
        bad='job_id,job_title\n100,Should roll back\n100,Repeated ID'
        self.assertEqual(self.bulk('job',bad,False).status_code,400)
        self.assertEqual(next(r['job_title'] for r in self.c.get('/api/records/job').json if r['job_id']==100),'New job')
    def archive_import(self,raw,preview=True,token=True):
        import io
        return self.c.post('/api/import-all',data={'file':(io.BytesIO(raw),'hr.zip'),'preview':str(preview).lower()},headers={'X-CSRF-Token':self.token} if token else {})
    def modify_zip(self,raw,name,text):
        import io,zipfile
        out=io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(raw)) as src,zipfile.ZipFile(out,'w') as dst:
            for item in src.namelist():dst.writestr(item,text if item==name else src.read(item))
        return out.getvalue()
    def test_archive_roundtrip_preview_cycles_and_updates(self):
        emp,dep,_=self.employee()
        self.c.put('/api/records/department/'+str(dep),json={'manager_id':emp,'description':'=formula-like text'},headers={'X-CSRF-Token':self.token})
        raw=self.c.get('/api/export-all').data
        preview=self.archive_import(raw)
        self.assertEqual(preview.status_code,200,preview.json)
        self.assertEqual(preview.json['updated'],3)
        self.assertEqual(self.c.get('/api/records/department').json[0]['manager_id'],emp)
        with engine.begin() as c:
            c.execute(metadata.tables['department'].update().values(manager_id=None))
            for table in reversed(list(metadata.tables.values())):c.execute(table.delete())
        self.assertEqual(self.archive_import(raw).json['created'],3)
        self.assertEqual(self.c.get('/api/summary').json['employee'],0)
        result=self.archive_import(raw,False)
        self.assertEqual(result.status_code,200,result.json)
        self.assertEqual(self.c.get('/api/records/employee').json[0]['employee_id'],emp)
        department=self.c.get('/api/records/department').json[0]
        self.assertEqual(department['manager_id'],emp)
        self.assertEqual(department['description'],'=formula-like text')
        self.post('job',{'job_title':'Keep this extra job'})
        self.assertEqual(self.archive_import(raw,False).json['updated'],3)
        self.assertEqual(self.c.get('/api/summary').json['job'],2)
        self.assertEqual(self.c.get('/api/summary').json['employee'],1)
    def test_archive_failure_rolls_back_every_section(self):
        self.employee()
        self.post('benefit',{'benefit_name':'Insurance','amount':'100'})
        raw=self.c.get('/api/export-all').data
        bad=self.modify_zip(raw,'benefit.csv','benefit_id,benefit_name,description,amount,frequency\n1,Insurance,,-100,')
        bad=self.modify_zip(bad,'job.csv','job_id,job_title,description,min_salary,max_salary,job_level\n1,Changed title,,,,')
        result=self.archive_import(bad,False)
        self.assertEqual(result.status_code,400,result.json)
        self.assertIn('benefit.csv',result.json['error'])
        self.assertEqual(self.c.get('/api/records/job').json[0]['job_title'],'Engineer')
        self.assertEqual(self.c.get('/api/records/benefit').json[0]['amount'],'100.00')
    def test_archive_structure_and_auth(self):
        import io,zipfile
        self.employee();raw=self.c.get('/api/export-all').data
        self.assertEqual(self.archive_import(raw,token=False).status_code,403)
        self.assertEqual(app.test_client().post('/api/import-all').status_code,401)
        self.assertEqual(self.archive_import(b'not a zip').status_code,400)
        out=io.BytesIO()
        with zipfile.ZipFile(out,'w') as archive:archive.writestr('../employee.csv','bad')
        self.assertEqual(self.archive_import(out.getvalue()).status_code,400)
        bad=self.modify_zip(raw,'employee.csv','employee_id,first_name\n1,Invalid')
        self.assertEqual(self.archive_import(bad).status_code,400)
if __name__=='__main__':unittest.main()
