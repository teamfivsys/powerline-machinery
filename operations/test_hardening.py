import hashlib
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
from unittest import TestCase as PlainTestCase
from django.test import TestCase, Client, override_settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from .models import Employee, Assignment, AuditEvent

# Additional tests preserve the existing provisional permissions: regular operators
# share allocation access; they are NOT employee-self-service accounts.
class HardeningTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        U = get_user_model()
        cls.admin = U.objects.create_superuser('security_admin', '', secrets.token_urlsafe(24))
        cls.operator = U.objects.create_user('security_operator', password=secrets.token_urlsafe(24))
        cls.other = U.objects.create_user('security_other', password=secrets.token_urlsafe(24))
        cls.staff = U.objects.create_user('security_staff', is_staff=True, password=secrets.token_urlsafe(24))
        cls.e = Employee.objects.create(name='Security Fictional Employee', joining_date='2026-01-01', salary_amount='98765.43', salary_currency='AED', salary_basis='test-only')
        cls.a = Assignment.objects.create(title='Security Fictional Allocation', employee=cls.e, created_by=cls.other)
    def setUp(self): cache.clear()
    def test_staff_flag_alone_does_not_grant_salary_access(self):
        self.client.force_login(self.staff)
        self.assertNotContains(self.client.get('/employees/'), '98765.43')
        self.assertEqual(self.client.get(f'/employees/{self.e.pk}/edit/').status_code, 403)
    def test_salary_absent_from_every_operator_page_including_object_edit(self):
        self.client.force_login(self.operator)
        for url in ['/', '/employees/', '/assignments/', '/assignments/new/', f'/assignments/{self.a.pk}/edit/', '/modules/crm/', '/modules/maintenance/', '/modules/field-tracking/']:
            with self.subTest(url=url): self.assertNotContains(self.client.get(url), '98765.43')
    def test_anonymous_cannot_modify_objects_by_id(self):
        self.assertEqual(self.client.post(f'/employees/{self.e.pk}/edit/', {'name': 'attack'}).status_code, 302)
        self.assertEqual(self.client.post(f'/assignments/{self.a.pk}/edit/', {'title': 'attack'}).status_code, 302)
        self.e.refresh_from_db(); self.a.refresh_from_db()
        self.assertEqual(self.e.name, 'Security Fictional Employee')
        self.assertEqual(self.a.title, 'Security Fictional Allocation')
    def test_operator_cannot_modify_salary_via_assignment_mass_assignment(self):
        self.client.force_login(self.operator)
        self.client.post(f'/assignments/{self.a.pk}/edit/', {'title':'Allowed edit', 'employee':self.e.pk, 'description':'test', 'salary_amount':'1', 'created_by':self.operator.pk})
        self.e.refresh_from_db(); self.a.refresh_from_db()
        self.assertEqual(str(self.e.salary_amount), '98765.43')
        self.assertEqual(self.a.created_by_id, self.other.pk)
        self.assertEqual(AuditEvent.objects.get().actor_id, self.operator.pk)
    def test_missing_object_is_404_for_authorized_user(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get('/employees/999999/edit/').status_code, 404)
        self.assertEqual(self.client.get('/assignments/999999/edit/').status_code, 404)
    def test_csrf_required_on_all_mutations(self):
        c = Client(enforce_csrf_checks=True); c.force_login(self.admin)
        for url in ['/employees/new/', f'/employees/{self.e.pk}/edit/', '/assignments/new/', f'/assignments/{self.a.pk}/edit/', '/password/change/', '/logout/']:
            with self.subTest(url=url): self.assertEqual(c.post(url, {}).status_code, 403)
    def test_failed_csrf_does_not_mutate(self):
        c = Client(enforce_csrf_checks=True); c.force_login(self.admin)
        c.post(f'/assignments/{self.a.pk}/edit/', {'title':'attack'})
        self.a.refresh_from_db(); self.assertEqual(self.a.title, 'Security Fictional Allocation')
        self.assertEqual(AuditEvent.objects.count(), 0)
    def test_session_key_rotates_on_login(self):
        password=secrets.token_urlsafe(24); self.operator.set_password(password); self.operator.save()
        session=self.client.session; session['probe']='test'; session.save(); before=session.session_key
        self.client.post('/login/', {'username':self.operator.username, 'password':password})
        self.assertNotEqual(self.client.session.session_key, before)
    def test_password_change_invalidates_other_sessions(self):
        old=secrets.token_urlsafe(24); new=secrets.token_urlsafe(24)
        self.operator.set_password(old); self.operator.save()
        other=Client(); self.client.login(username=self.operator.username,password=old); other.login(username=self.operator.username,password=old)
        r=self.client.post('/password/change/', {'old_password':old,'new_password1':new,'new_password2':new})
        self.assertEqual(r.status_code,302)
        self.assertEqual(self.client.get('/').status_code,200)
        self.assertEqual(other.get('/').status_code,302)
    def test_deactivation_invalidates_existing_session(self):
        self.client.force_login(self.operator)
        self.operator.is_active=False; self.operator.save()
        self.assertEqual(self.client.get('/').status_code,302)
    def test_no_store_on_logout_and_anonymous_redirect(self):
        self.client.force_login(self.operator)
        self.assertEqual(self.client.post('/logout/')['Cache-Control'],'no-store, private')
        self.assertEqual(self.client.get('/employees/')['Cache-Control'],'no-store, private')
    def test_user_throttle_not_bypassed_by_ip_change(self):
        key='login-user:'+hashlib.sha256(self.operator.username.encode()).hexdigest(); cache.set(key,10,900)
        self.assertEqual(self.client.post('/login/',{'username':self.operator.username,'password':'wrong'},REMOTE_ADDR='192.0.2.10').status_code,429)
    @override_settings(SESSION_COOKIE_SECURE=True, CSRF_COOKIE_SECURE=True, SESSION_COOKIE_HTTPONLY=True)
    def test_secure_session_cookie_flags(self):
        self.client.force_login(self.operator)
        r=self.client.get('/login/',secure=True)
        self.assertTrue(r.cookies['csrftoken']['secure'])

class ProductionConfigTests(PlainTestCase):
    def config(self, **changes):
        env={**os.environ,'DJANGO_SETTINGS_MODULE':'config.production','DJANGO_SECRET_KEY':secrets.token_urlsafe(64),'DJANGO_DEBUG':'0','DJANGO_ALLOWED_HOSTS':'powerline.example','DJANGO_DB_PATH':'/tmp/powerline-private/data.sqlite3'}
        env.pop("DATABASE_URL", None) # this profile tests the preserved SQLite host mode
        env.update(changes)
        return subprocess.run([sys.executable,'-c','import django; django.setup()'],env=env,capture_output=True,text=True)
    def test_valid_profile_imports(self): self.assertEqual(self.config().returncode,0)
    def test_rejects_debug(self): self.assertNotEqual(self.config(DJANGO_DEBUG='1').returncode,0)
    def test_rejects_weak_secret(self): self.assertNotEqual(self.config(DJANGO_SECRET_KEY='weak').returncode,0)
    def test_rejects_wildcard_hosts(self): self.assertNotEqual(self.config(DJANGO_ALLOWED_HOSTS='*').returncode,0)
    def test_rejects_unspecified_hosts(self): self.assertNotEqual(self.config(DJANGO_ALLOWED_HOSTS='').returncode,0)
    def test_rejects_relative_database(self): self.assertNotEqual(self.config(DJANGO_DB_PATH='data.sqlite3').returncode,0)
    def test_rejects_source_database(self): self.assertNotEqual(self.config(DJANGO_DB_PATH=str(Path.cwd()/'data.sqlite3')).returncode,0)
    def test_rejects_insecure_csrf_origin(self): self.assertNotEqual(self.config(DJANGO_CSRF_TRUSTED_ORIGINS='http://powerline.example').returncode,0)
