import os,tempfile,unittest
_tmp=tempfile.TemporaryDirectory()
os.environ['DATABASE_URL']='sqlite:///'+_tmp.name+'/test.db'
os.environ['HR_ADMIN_PASSWORD']='test-only-password'
from app import app,metadata,engine
class HRTests(unittest.TestCase):
    def setUp(self):
        with engine.begin() as c:
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
        for text in ['description\nMissing name','job_title,job_title\nA,B','job_id,job_title\n1,A','job_title,description\nA,B,C']:
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
if __name__=='__main__':unittest.main()
