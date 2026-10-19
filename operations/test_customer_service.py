from datetime import date
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db.models import ProtectedError
from django.test import TestCase, Client
from .models import Employee, Enquiry, ServiceJob, AuditEvent

class CustomerServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        U = get_user_model()
        cls.admin = U.objects.create_superuser('module_admin', '', 'FictionalTestPass!459')
        cls.operator = U.objects.create_user('module_operator', password='FictionalTestPass!358')
        cls.staff = U.objects.create_user('module_staff', password='FictionalTestPass!258', is_staff=True)
        cls.employee = Employee.objects.create(name='Fictional Technician', joining_date=date(2026,1,1), salary_amount='98765.43',salary_currency='AED',salary_basis='monthly')
        cls.enquiry = Enquiry.objects.create(customer_name='Private Customer',contact='test@example.invalid',kind='service',summary='Forklift service request',details='Fictional fault request',created_by=cls.admin)
        cls.spares = Enquiry.objects.create(customer_name='Spares Customer',kind='spares',summary='Spare part enquiry',details='Fictional part details',created_by=cls.admin)
        cls.job = ServiceJob.objects.create(customer_name='Private Customer',enquiry=cls.enquiry,machine='Fictional forklift A',fault='Fictional fault',technician=cls.employee,created_by=cls.admin)
    def setUp(self):
        cache.clear()
    def enquiry_data(self, **kw):
        return dict(customer_name='New Customer',contact='contact@example.invalid',kind='service',summary='Forklift enquiry',details='Fictional service details',status='open',follow_up_notes='',closure_outcome='',**kw) if not kw else {**self.enquiry_data(),**kw}
    def job_data(self, **kw):
        return {**dict(customer_name='New Customer',enquiry=self.enquiry.pk,machine='Fictional forklift B',fault='Fictional lifting fault',technician=self.employee.pk,status='open',work_done=''), **kw}
    def login(self): self.client.force_login(self.admin)
    def routes(self): return ['/crm/','/crm/new/',f'/crm/{self.enquiry.pk}/edit/','/maintenance/','/maintenance/new/',f'/maintenance/{self.job.pk}/edit/']
    def test_anonymous_routes_require_login(self):
        for path in self.routes():
            self.assertEqual(self.client.get(path).status_code,302)
            self.assertEqual(self.client.post(path,{}).status_code,302)
    def test_operator_routes_deny_get_and_post(self):
        self.client.force_login(self.operator)
        for path in self.routes():
            for response in [self.client.get(path),self.client.post(path,{})]:
                self.assertEqual(response.status_code,403)
                self.assertNotContains(response,'Private Customer',status_code=403)
        self.assertEqual(Enquiry.objects.count(),2);self.assertEqual(ServiceJob.objects.count(),1)
    def test_staff_flag_alone_does_not_grant_access(self):
        self.client.force_login(self.staff)
        for path in self.routes(): self.assertEqual(self.client.get(path).status_code,403)
    def test_operator_dashboard_hides_customer_data_and_counts(self):
        self.client.force_login(self.operator)
        r=self.client.get('/')
        for text in ['Private Customer','Open enquiries','Active service jobs','Customer enquiries','Maintenance jobs']:
            self.assertNotContains(r,text)
    def test_create_enquiry_persist_reopen(self):
        self.login();r=self.client.post('/crm/new/',self.enquiry_data())
        self.assertRedirects(r,'/crm/')
        item=Enquiry.objects.get(customer_name='New Customer')
        self.assertEqual(item.created_by,self.admin)
        self.assertContains(self.client.get(f'/crm/{item.pk}/edit/'),'Fictional service details')
        self.assertContains(self.client.get('/crm/'),'New Customer')
    def test_enquiry_update_follow_up_and_close(self):
        self.login();self.client.post(f'/crm/{self.enquiry.pk}/edit/',self.enquiry_data(status='closed',follow_up_notes='Customer called back',closure_outcome='Service handled; no sale implied'))
        self.enquiry.refresh_from_db();self.assertEqual(self.enquiry.status,'closed');self.assertEqual(self.enquiry.follow_up_notes,'Customer called back')
        self.assertContains(self.client.get('/crm/?status=closed'),'Service handled; no sale implied')
    def test_enquiry_close_requires_outcome(self):
        self.login();r=self.client.post(f'/crm/{self.enquiry.pk}/edit/',self.enquiry_data(status='closed',closure_outcome='  '))
        self.assertContains(r,'Record the enquiry outcome')
        self.enquiry.refresh_from_db();self.assertEqual(self.enquiry.status,'open')
    def test_closed_enquiry_can_reopen(self):
        self.login();url=f'/crm/{self.enquiry.pk}/edit/'
        self.client.post(url,self.enquiry_data(status='closed',closure_outcome='Awaiting new request'))
        self.client.post(url,self.enquiry_data(status='in_progress',closure_outcome='Previous outcome retained',follow_up_notes='New follow-up'))
        self.enquiry.refresh_from_db();self.assertEqual(self.enquiry.status,'in_progress')
    def test_enquiry_validation_required(self):
        self.login();self.client.post('/crm/new/',self.enquiry_data(customer_name='  ',details='  '))
        self.assertEqual(Enquiry.objects.count(),2)
    def test_invalid_enquiry_status_rejected(self):
        self.login();self.client.post('/crm/new/',self.enquiry_data(status='paid'))
        self.assertEqual(Enquiry.objects.count(),2)
    def test_invalid_enquiry_kind_rejected(self):
        self.login();self.client.post('/crm/new/',self.enquiry_data(kind='inventory'))
        self.assertEqual(Enquiry.objects.count(),2)
    def test_enquiry_lengths_rejected(self):
        self.login();self.client.post('/crm/new/',self.enquiry_data(summary='x'*181))
        self.assertEqual(Enquiry.objects.count(),2)
    def test_enquiry_created_by_forgery_ignored(self):
        self.login();self.client.post('/crm/new/',self.enquiry_data(created_by=self.operator.pk))
        self.assertEqual(Enquiry.objects.get(customer_name='New Customer').created_by,self.admin)
    def test_service_create_persist_reopen(self):
        self.login();self.assertRedirects(self.client.post('/maintenance/new/',self.job_data()),'/maintenance/')
        item=ServiceJob.objects.get(machine='Fictional forklift B')
        self.assertEqual(item.technician,self.employee);self.assertEqual(item.enquiry,self.enquiry)
        self.assertContains(self.client.get(f'/maintenance/{item.pk}/edit/'),'Fictional lifting fault')
        self.assertContains(self.client.get('/maintenance/'),'Fictional Technician')
    def test_service_create_without_enquiry(self):
        self.login();self.client.post('/maintenance/new/',self.job_data(enquiry=''))
        self.assertIsNone(ServiceJob.objects.get(machine='Fictional forklift B').enquiry)
    def test_service_complete_requires_work(self):
        self.login();r=self.client.post(f'/maintenance/{self.job.pk}/edit/',self.job_data(status='completed',work_done='  '))
        self.assertContains(r,'Record the work done')
        self.job.refresh_from_db();self.assertEqual(self.job.status,'open')
    def test_service_complete_then_reopen(self):
        self.login();url=f'/maintenance/{self.job.pk}/edit/'
        self.client.post(url,self.job_data(status='completed',work_done='Fictional repair recorded'))
        self.job.refresh_from_db();self.assertEqual(self.job.status,'completed')
        self.assertContains(self.client.get('/maintenance/?status=completed'),'Fictional repair recorded')
        self.client.post(url,self.job_data(status='in_progress',work_done='Further inspection needed'))
        self.job.refresh_from_db();self.assertEqual(self.job.status,'in_progress')
    def test_invalid_technician_rejected(self):
        self.login();self.client.post('/maintenance/new/',self.job_data(technician=999999))
        self.assertEqual(ServiceJob.objects.count(),1)
    def test_missing_technician_rejected(self):
        self.login();self.client.post('/maintenance/new/',self.job_data(technician=''))
        self.assertEqual(ServiceJob.objects.count(),1)
    def test_spares_enquiry_link_rejected(self):
        self.login();self.client.post('/maintenance/new/',self.job_data(enquiry=self.spares.pk))
        self.assertEqual(ServiceJob.objects.count(),1)
    def test_linked_enquiry_cannot_change_to_spares(self):
        self.login();r=self.client.post(f'/crm/{self.enquiry.pk}/edit/',self.enquiry_data(kind='spares'))
        self.assertContains(r,'Keep its type as Service')
        self.enquiry.refresh_from_db();self.assertEqual(self.enquiry.kind,'service')
    def test_service_fields_required(self):
        self.login();self.client.post('/maintenance/new/',self.job_data(machine='',fault=''))
        self.assertEqual(ServiceJob.objects.count(),1)
    def test_service_invalid_status_rejected(self):
        self.login();self.client.post('/maintenance/new/',self.job_data(status='paid'))
        self.assertEqual(ServiceJob.objects.count(),1)
    def test_service_created_by_forgery_ignored(self):
        self.login();self.client.post('/maintenance/new/',self.job_data(created_by=self.operator.pk))
        self.assertEqual(ServiceJob.objects.get(machine='Fictional forklift B').created_by,self.admin)
    def test_records_remain_separate_from_shared_allocations(self):
        from .models import Assignment
        self.login();self.client.post('/maintenance/new/',self.job_data())
        self.assertEqual(Assignment.objects.count(),0)
    def test_completion_does_not_automatically_close_enquiry(self):
        self.login();self.client.post(f'/maintenance/{self.job.pk}/edit/',self.job_data(status='completed',work_done='Fictional repair'))
        self.enquiry.refresh_from_db();self.assertEqual(self.enquiry.status,'open')
    def test_status_filter_and_invalid_filter(self):
        self.login();self.assertNotContains(self.client.get('/crm/?status=closed'),'Private Customer')
        self.assertNotContains(self.client.get('/maintenance/?status=completed'),'Fictional forklift A')
        self.assertContains(self.client.get('/crm/?status=bad'),'Private Customer')
    def test_unknown_records_404(self):
        self.login()
        for url in ['/crm/99999/edit/','/maintenance/99999/edit/']: self.assertEqual(self.client.get(url).status_code,404)
    def test_csrf_required_for_each_mutation(self):
        c=Client(enforce_csrf_checks=True);c.force_login(self.admin)
        for url in ['/crm/new/',f'/crm/{self.enquiry.pk}/edit/','/maintenance/new/',f'/maintenance/{self.job.pk}/edit/']:
            self.assertEqual(c.post(url,{}).status_code,403)
    def test_audit_identifiers_not_sensitive_payload(self):
        self.login();self.client.post('/crm/new/',self.enquiry_data());self.client.post('/maintenance/new/',self.job_data())
        self.assertEqual(list(AuditEvent.objects.values_list('action',flat=True)),['enquiry_created','service_job_created'])
        self.assertNotIn('New Customer',str(list(AuditEvent.objects.values())))
    def test_all_new_views_private_and_escape_input(self):
        self.enquiry.details='<script>alert(1)</script>';self.enquiry.save()
        self.job.fault='<script>alert(1)</script>';self.job.save()
        self.login()
        for url in self.routes():
            r=self.client.get(url);self.assertEqual(r['Cache-Control'],'no-store, private')
            self.assertNotContains(r,'<script>alert(1)</script>');self.assertNotContains(r,'98765.43')
        self.assertContains(self.client.get('/crm/'),'&lt;script&gt;')
        self.assertContains(self.client.get('/maintenance/'),'&lt;script&gt;')
    def test_new_views_do_not_load_salary_fields(self):
        from django.test.utils import CaptureQueriesContext
        from django.db import connection
        self.login()
        for url in ['/maintenance/','/maintenance/new/',f'/maintenance/{self.job.pk}/edit/']:
            with CaptureQueriesContext(connection) as ctx: self.client.get(url)
            for q in ctx: self.assertNotIn('salary_amount',q['sql'])
    def test_protect_technician_and_enquiry_relations(self):
        with self.assertRaises(ProtectedError): self.employee.delete()
        with self.assertRaises(ProtectedError): self.enquiry.delete()
