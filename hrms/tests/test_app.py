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
    def test_payroll_and_dates(self):
        emp,_,_=self.employee()
        self.assertEqual(self.post('payroll',{'employee_id':emp,'pay_period':'2026-10','basic_salary':'1000','allowances':'100','deductions':'50','net_salary':'9999','payment_status':'Pending'}).status_code,200)
        self.assertEqual(self.c.get('/api/records/payroll').json[0]['net_salary'],'1050.00')
        self.assertEqual(self.post('training',{'training_name':'Bad dates','start_date':'2026-10-20','end_date':'2026-10-01'}).status_code,400)
        self.assertEqual(self.post('attendance',{'employee_id':9999,'attendance_date':'2026-10-24','status':'Present'}).status_code,400)
if __name__=='__main__':unittest.main()
