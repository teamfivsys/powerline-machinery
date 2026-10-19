"""Deployment preparation checks; all credentials and hosts are fictional."""
from datetime import timedelta
import os
from pathlib import Path
import secrets
import subprocess
import sys
from unittest import TestCase as PlainTestCase
from django.test import TestCase, override_settings
from django.core.exceptions import ImproperlyConfigured
from django.utils import timezone
from django.contrib.auth import get_user_model
from config.database import postgres_database
from operations.models import Employee, ServiceJob, LocationShare

class DatabaseURLTests(PlainTestCase):
    def test_percent_encoded_credentials_and_pooler_safety(self):
        d = postgres_database('postgresql://test%40name:p%2Fword@db.example/testdb?sslmode=require')
        self.assertEqual(d['USER'], 'test@name'); self.assertEqual(d['PASSWORD'], 'p/word')
        self.assertEqual(d['CONN_MAX_AGE'], 0); self.assertTrue(d['DISABLE_SERVER_SIDE_CURSORS'])
    def test_provider_channel_binding_supported(self):
        d=postgres_database("postgres://a:b@db.example/d?sslmode=verify-full&channel_binding=require")
        self.assertEqual(d["OPTIONS"]["channel_binding"],"require")
        self.assertTrue(d["CONN_HEALTH_CHECKS"])
    def test_default_verifies_certificate(self):
        self.assertEqual(postgres_database('postgres://a:b@db.example/d')['OPTIONS']['sslmode'],'verify-full')
    def test_disallow_insecure_production_urls(self):
        for u in ['sqlite:///tmp/a','postgres://a:b@db.example/d?sslmode=disable','postgres://a:b@db.example/d?sslmode=prefer','postgres://a:b@db.example/d?options=x','postgres://a:b@db.example/d?sslmode=require&sslmode=disable','postgres://a:b@db.example/d#secret','postgres://db.example/d']:
            with self.subTest(url=u):
                with self.assertRaises(ImproperlyConfigured): postgres_database(u)
    def test_allow_disable_only_explicit_local_development(self):
        self.assertEqual(postgres_database('postgres://a:b@127.0.0.1/d?sslmode=disable',allow_local_insecure=True)['OPTIONS']['sslmode'],'disable')
        with self.assertRaises(ImproperlyConfigured): postgres_database('postgres://a:b@remote.example/d?sslmode=disable',allow_local_insecure=True)
    def test_error_never_contains_url_secret(self):
        with self.assertRaises(ImproperlyConfigured) as c: postgres_database('postgres://test:private-marker@db/d?bad=1')
        self.assertNotIn('private-marker', str(c.exception))

class VercelConfigTests(PlainTestCase):
    def check(self, **changes):
        env={**os.environ,'VERCEL':'1','DJANGO_SETTINGS_MODULE':'config.vercel','DJANGO_DEBUG':'0','DJANGO_SECRET_KEY':secrets.token_urlsafe(64),'DJANGO_ALLOWED_HOSTS':'powerline.example','DATABASE_URL':'postgres://a:b@db.example/powerline?sslmode=require'}
        env.pop('DJANGO_DB_PATH',None);env.update(changes)
        return subprocess.run([sys.executable,'-c','import django; django.setup(); from django.conf import settings; assert settings.SESSION_ENGINE == "django.contrib.sessions.backends.db"; assert settings.SECURE_PROXY_SSL_HEADER == ("HTTP_X_FORWARDED_PROTO", "https")'],env=env,capture_output=True)
    def test_valid_vercel_profile_imports_without_db_connection(self): self.assertEqual(self.check().returncode,0)
    def test_reject_explicit_development_profile_on_vercel(self): self.assertNotEqual(self.check(DJANGO_SETTINGS_MODULE='config.settings').returncode,0)
    def test_reject_generic_production_profile_on_vercel(self): self.assertNotEqual(self.check(DJANGO_SETTINGS_MODULE='config.production').returncode,0)
    def test_no_sqlite_fallback(self): self.assertNotEqual(self.check(DATABASE_URL='',DJANGO_DB_PATH='/tmp/never.sqlite3').returncode,0)
    def test_reject_debug(self): self.assertNotEqual(self.check(DJANGO_DEBUG='1').returncode,0)
    def test_reject_platform_marker_missing(self): self.assertNotEqual(self.check(VERCEL='0').returncode,0)
    def test_reject_weak_secret_and_wildcard(self):
        self.assertNotEqual(self.check(DJANGO_SECRET_KEY='weak').returncode,0)
        self.assertNotEqual(self.check(DJANGO_ALLOWED_HOSTS='*.vercel.app').returncode,0)

class CronTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin=get_user_model().objects.create_superuser('cron_admin','',secrets.token_urlsafe(24))
        e=Employee.objects.create(name='Fictional',joining_date='2026-01-01',salary_amount='1',salary_currency='AED',salary_basis='test')
        j=ServiceJob.objects.create(customer_name='Fictional',machine='Test',fault='Test',technician=e,created_by=cls.admin)
        cls.share=LocationShare.objects.create(job=j,user=cls.admin,started_at=timezone.now(),expires_at=timezone.now()-timedelta(seconds=1),token=secrets.token_hex(16))
    def test_disabled_by_default(self):
        with override_settings(CRON_SECRET=''):
            self.assertEqual(self.client.get('/internal/cron/purge-locations/').status_code,503)
            self.assertEqual(LocationShare.objects.count(),1)
    @override_settings(CRON_SECRET='a'*40)
    def test_auth_required_even_for_admin(self):
        self.client.force_login(self.admin)
        for headers in ({},{'HTTP_AUTHORIZATION':'Bearer wrong'}): self.assertEqual(self.client.get('/internal/cron/purge-locations/',**headers).status_code,401)
        self.assertEqual(LocationShare.objects.count(),1)
    @override_settings(CRON_SECRET='a'*40)
    def test_authorized_cleanup_idempotent_and_no_location_response(self):
        r=self.client.get('/internal/cron/purge-locations/',HTTP_AUTHORIZATION='Bearer '+'a'*40)
        self.assertEqual(r.json(),{'deleted':1});self.assertEqual(r['Cache-Control'],'no-store, private')
        self.assertEqual(self.client.get('/internal/cron/purge-locations/',HTTP_AUTHORIZATION='Bearer '+'a'*40).json(),{'deleted':0})
    @override_settings(CRON_SECRET='a'*40)
    def test_only_get(self): self.assertEqual(self.client.post('/internal/cron/purge-locations/',HTTP_AUTHORIZATION='Bearer '+'a'*40).status_code,405)
    def test_dispatcher_loads_expiry_script_without_location_permission(self):
        self.client.force_login(self.admin)
        r=self.client.get('/dispatcher/')
        self.assertContains(r,'dispatcher-expiry.js');self.assertEqual(r['Permissions-Policy'],'geolocation=()')
        self.assertIn("script-src 'self'",r['Content-Security-Policy'])
