from datetime import timedelta
from io import StringIO
import secrets
import uuid
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command, CommandError
from django.test import TestCase, Client
from django.utils import timezone
from .models import Employee, ServiceJob, TechnicianAccess, LocationShare

class ForegroundLocationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        U=get_user_model()
        cls.admin=U.objects.create_superuser('dispatch_admin','','FictionalTestPass!928')
        cls.tech=U.objects.create_user('tech_a',password='FictionalTestPass!128')
        cls.other=U.objects.create_user('tech_b',password='FictionalTestPass!228')
        cls.operator=U.objects.create_user('unmapped',password='FictionalTestPass!328')
        cls.employee=Employee.objects.create(name='Fictional Tech A',joining_date='2026-01-01',salary_amount='65432.17',salary_currency='AED',salary_basis='monthly')
        cls.employee_b=Employee.objects.create(name='Fictional Tech B',joining_date='2026-01-01',salary_amount='75432.17',salary_currency='AED',salary_basis='monthly')
        TechnicianAccess.objects.create(user=cls.tech,employee=cls.employee)
        TechnicianAccess.objects.create(user=cls.other,employee=cls.employee_b)
        cls.job=ServiceJob.objects.create(customer_name='Job A customer',machine='Test machine A',fault='Test fault A',technician=cls.employee,created_by=cls.admin)
        cls.job_b=ServiceJob.objects.create(customer_name='Job B customer',machine='Test machine B',fault='Test fault B',technician=cls.employee_b,created_by=cls.admin)
    def setUp(self):cache.clear();self.client.force_login(self.tech)
    def url(self,action,job=None):return f'/my-service/{(job or self.job).pk}/location/{action}/'
    def start(self):
        r=self.client.post(self.url('start'),{'consent':'foreground'});self.assertEqual(r.status_code,200);return r.json()['token']
    def ping(self,token,**kw):
        return self.client.post(self.url('ping'),{**dict(token=token,latitude='0.123456',longitude='0.654321',accuracy_m='12.3',captured_at=timezone.now().isoformat()),**kw})
    def test_assignment_scoped_list_and_detail(self):
        self.assertContains(self.client.get('/my-service/'),'Test machine A')
        self.assertNotContains(self.client.get('/my-service/'),'Test machine B')
        self.assertEqual(self.client.get(f'/my-service/{self.job_b.pk}/').status_code,404)
        self.assertNotContains(self.client.get(f'/my-service/{self.job.pk}/'),'65432.17')
    def test_tech_cannot_open_crm_admin_maintenance_or_dispatcher(self):
        for path in ['/crm/','/maintenance/','/dispatcher/']:
            self.assertEqual(self.client.get(path).status_code,403)
    def test_unmapped_user_has_no_technician_access(self):
        self.client.force_login(self.operator)
        self.assertEqual(self.client.get('/my-service/').status_code,403)
        for action in ['start','ping','stop']:self.assertEqual(self.client.post(self.url(action),{}).status_code,403)
    def test_other_technician_cannot_start_ping_or_stop_others_job(self):
        token=self.start();self.client.force_login(self.other)
        for action in ['start','ping','stop']:self.assertEqual(self.client.post(self.url(action),{'token':token,'consent':'foreground'}).status_code,404)
        self.assertEqual(LocationShare.objects.count(),1)
    def test_anonymous_all_technician_routes_require_login(self):
        self.client.logout()
        for path in ['/my-service/',f'/my-service/{self.job.pk}/','/dispatcher/']+[self.url(a) for a in ['start','ping','stop']]:
            self.assertEqual(self.client.get(path).status_code,302)
    def test_start_requires_explicit_consent(self):
        self.assertEqual(self.client.post(self.url('start'),{}).status_code,400)
        self.assertEqual(LocationShare.objects.count(),0)
    def test_start_stores_no_coordinates(self):
        self.start();s=LocationShare.objects.get()
        self.assertIsNone(s.latitude);self.assertIsNone(s.captured_at)
        self.assertLessEqual((s.expires_at-timezone.now()).total_seconds(),120)
    def test_sample_saved_as_latest_not_trail(self):
        token=self.start();self.assertEqual(self.ping(token).status_code,200)
        self.assertEqual(self.ping(token,latitude='1.234567').status_code,200)
        self.assertEqual(LocationShare.objects.count(),1)
        self.assertEqual(LocationShare.objects.get().latitude,1.234567)
    def test_missing_or_wrong_token_does_not_write(self):
        self.start();self.assertEqual(self.ping(str(uuid.uuid4())).status_code,409)
        self.assertEqual(self.ping('').status_code,400)
        self.assertIsNone(LocationShare.objects.get().latitude)
    def test_forged_user_and_job_fields_cannot_impersonate(self):
        token=self.start();self.ping(token,user=self.other.pk,job=self.job_b.pk)
        s=LocationShare.objects.get();self.assertEqual(s.user,self.tech);self.assertEqual(s.job,self.job)
    def test_non_finite_and_out_of_range_samples_rejected(self):
        token=self.start()
        for fields in [dict(latitude='nan'),dict(latitude='inf'),dict(latitude='91'),dict(longitude='181'),dict(accuracy_m='-1'),dict(accuracy_m='nan'),dict(accuracy_m='100001'),dict(latitude='not a number')]:
            self.assertEqual(self.ping(token,**fields).status_code,400)
        self.assertIsNone(LocationShare.objects.get().latitude)
    def test_capture_time_must_be_recent_and_timezone_aware(self):
        token=self.start()
        for stamp in ['invalid','2026-10-19T10:00:00',(timezone.now()-timedelta(minutes=3)).isoformat(),(timezone.now()+timedelta(minutes=3)).isoformat()]:
            self.assertEqual(self.ping(token,captured_at=stamp).status_code,400)
    def test_old_sample_cannot_extend_expiry_beyond_capture_plus_two_minutes(self):
        token=self.start();captured=timezone.now()-timedelta(seconds=90)
        self.ping(token,captured_at=captured.isoformat())
        self.assertLessEqual((LocationShare.objects.get().expires_at-captured).total_seconds(),120)
    def test_out_of_order_samples_rejected(self):
        token=self.start();self.ping(token)
        self.assertEqual(self.ping(token,captured_at=(timezone.now()-timedelta(seconds=10)).isoformat()).status_code,400)
    def test_stop_deletes_coordinates_and_late_ping_fails(self):
        token=self.start();self.ping(token)
        self.assertEqual(self.client.post(self.url('stop'),{'token':token}).status_code,200)
        self.assertEqual(LocationShare.objects.count(),0)
        self.assertEqual(self.ping(token).status_code,409)
    def test_previous_tab_cannot_stop_new_session(self):
        old=self.start();new=self.start();self.client.post(self.url('stop'),{'token':old})
        self.assertEqual(str(LocationShare.objects.get().token),new)
    def test_expired_session_is_deleted_and_cannot_ping(self):
        token=self.start();LocationShare.objects.update(expires_at=timezone.now()-timedelta(seconds=1))
        self.assertEqual(self.ping(token).status_code,409);self.assertEqual(LocationShare.objects.count(),0)
    def test_dispatcher_admin_only_recent_stale_and_expired_labels(self):
        token=self.start();self.ping(token,captured_at=(timezone.now()-timedelta(seconds=45)).isoformat())
        self.client.force_login(self.admin);r=self.client.get('/dispatcher/')
        self.assertContains(r,'Stale');self.assertContains(r,'0.123456');self.assertContains(r,'12.3 m');self.assertContains(r,'Captured')
        LocationShare.objects.update(expires_at=timezone.now()-timedelta(seconds=1))
        self.assertNotContains(self.client.get('/dispatcher/'),'0.123456')
        self.assertEqual(LocationShare.objects.count(),0)
    def test_mapping_removal_revokes_dispatcher_sample(self):
        token=self.start();self.ping(token);TechnicianAccess.objects.filter(user=self.tech).delete()
        self.client.force_login(self.admin);self.assertNotContains(self.client.get('/dispatcher/'),'0.123456')
        self.assertEqual(LocationShare.objects.count(),0)
    def test_reassignment_revokes_old_technician_access(self):
        token=self.start();self.ping(token);self.job.technician=self.employee_b;self.job.save()
        self.assertEqual(self.ping(token).status_code,404)
        self.client.force_login(self.admin);self.assertNotContains(self.client.get('/dispatcher/'),'0.123456')
    def test_disabled_user_cannot_upload(self):
        token=self.start();self.tech.is_active=False;self.tech.save()
        self.assertEqual(self.ping(token).status_code,302)
    def test_tech_can_complete_and_reopen_only_own_job(self):
        token=self.start();self.ping(token)
        r=self.client.post(f'/my-service/{self.job.pk}/',{'status':'completed','work_done':'Fictional inspection completed','technician':self.employee_b.pk,'customer_name':'Forged'})
        self.assertEqual(r.status_code,302);self.job.refresh_from_db()
        self.assertEqual(self.job.status,'completed');self.assertEqual(self.job.technician_id,self.employee.pk);self.assertEqual(self.job.customer_name,'Job A customer')
        self.assertEqual(LocationShare.objects.count(),0)
        self.client.post(f'/my-service/{self.job.pk}/',{'status':'in_progress','work_done':'Reopened for test'})
        self.job.refresh_from_db();self.assertEqual(self.job.status,'in_progress')
    def test_tech_completion_requires_work_done(self):
        r=self.client.post(f'/my-service/{self.job.pk}/',{'status':'completed','work_done':'  '})
        self.assertContains(r,'Record the work done');self.job.refresh_from_db();self.assertEqual(self.job.status,'open')
    def test_completed_jobs_cannot_start_sharing(self):
        self.job.status='completed';self.job.work_done='Test';self.job.save()
        self.assertEqual(self.client.post(self.url('start'),{'consent':'foreground'}).status_code,409)
    def test_endpoints_post_only_and_csrf_required(self):
        c=Client(enforce_csrf_checks=True);c.force_login(self.tech)
        for a in ['start','ping','stop']:
            self.assertEqual(c.get(self.url(a)).status_code,405)
            self.assertEqual(c.post(self.url(a),{}).status_code,403)
        self.assertEqual(c.post(f'/my-service/{self.job.pk}/',{}).status_code,403)
    def test_script_policy_limited_to_technician_routes_and_no_inline_script(self):
        r=self.client.get(f'/my-service/{self.job.pk}/')
        self.assertIn("script-src 'self'",r['Content-Security-Policy'])
        self.assertEqual(r['Permissions-Policy'],'geolocation=(self)')
        self.assertEqual(r['Cache-Control'],'no-store, private')
        r=self.client.get('/');self.assertIn("script-src 'none'",r['Content-Security-Policy']);self.assertEqual(r['Permissions-Policy'],'geolocation=()')
    def test_purge_command_deletes_expired_only(self):
        self.start();call_command('purge_locations',stdout=StringIO());self.assertEqual(LocationShare.objects.count(),1)
        LocationShare.objects.update(expires_at=timezone.now()-timedelta(seconds=1))
        call_command('purge_locations',stdout=StringIO());self.assertEqual(LocationShare.objects.count(),0)
    def test_link_command_requires_explicit_unambiguous_existing_accounts(self):
        with self.assertRaises(CommandError):call_command('link_technician','dispatch_admin',self.employee.pk,stdout=StringIO())
        with self.assertRaises(CommandError):call_command('link_technician','unmapped',self.employee.pk,stdout=StringIO())
        TechnicianAccess.objects.filter(user=self.tech).delete()
        call_command('link_technician','unmapped',self.employee.pk,stdout=StringIO())
        self.assertEqual(TechnicianAccess.objects.get(user=self.operator).employee_id,self.employee.pk)
    def test_create_technician_command_and_unlink(self):
        from unittest.mock import patch
        e=Employee.objects.create(name='Provision Test',joining_date='2026-01-01',salary_amount='0',salary_currency='AED',salary_basis='test')
        with patch('operations.management.commands.create_technician.getpass',return_value='FictionalNewPass!4692'):
            call_command('create_technician','provisioned',e.pk,stdout=StringIO())
        u=get_user_model().objects.get(username='provisioned')
        self.assertFalse(u.is_superuser);self.assertFalse(u.is_staff);self.assertTrue(u.check_password('FictionalNewPass!4692'))
        self.assertEqual(u.technician_access.employee,e)
        call_command('unlink_technician','provisioned',stdout=StringIO())
        self.assertFalse(TechnicianAccess.objects.filter(user=u).exists())
    def test_create_technician_command_rejects_password_mismatch(self):
        from unittest.mock import patch
        e=Employee.objects.create(name='Provision Test',joining_date='2026-01-01',salary_amount='0',salary_currency='AED',salary_basis='test')
        with patch('operations.management.commands.create_technician.getpass',side_effect=['a','b']):
            with self.assertRaises(CommandError):call_command('create_technician','provisioned',e.pk,stdout=StringIO())
        self.assertFalse(get_user_model().objects.filter(username='provisioned').exists())

    def test_late_ping_cannot_write_after_concurrent_completion(self):
        from unittest.mock import patch
        token=self.start()
        stale=ServiceJob.objects.get(pk=self.job.pk)
        ServiceJob.objects.filter(pk=self.job.pk).update(status="completed", work_done="Test complete")
        with patch("operations.location_views.assigned_job",return_value=stale):
            self.assertEqual(self.ping(token).status_code,409)
        self.assertIsNone(LocationShare.objects.get().latitude)
    def test_late_ping_cannot_overwrite_newer_concurrent_sample(self):
        from unittest.mock import patch
        from django.db.models.query import QuerySet
        token=self.start();old=timezone.now()-timedelta(seconds=10);newer=timezone.now()
        LocationShare.objects.update(captured_at=old,latitude=1.0)
        original=QuerySet.first
        def race(query):
            result=original(query)
            if query.model is LocationShare and result:
                LocationShare.objects.filter(pk=result.pk).update(captured_at=newer,latitude=2.0)
            return result
        with patch.object(QuerySet,"first",race):
            self.assertEqual(self.ping(token,captured_at=(old+timedelta(seconds=1)).isoformat(),latitude='3.0').status_code,409)
        self.assertEqual(LocationShare.objects.get().latitude,2.0)
