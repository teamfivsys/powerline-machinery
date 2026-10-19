"""No network or real credentials: new Render guards and packaging checks."""
import os, secrets, subprocess, sys
from pathlib import Path
from unittest import TestCase
ROOT=Path(__file__).resolve().parents[1]
class RenderProfileTests(TestCase):
    def check(self, **changes):
        env={**os.environ, 'RENDER':'true','VERCEL':'0','DJANGO_SETTINGS_MODULE':'config.render','DJANGO_DEBUG':'0','DJANGO_SECRET_KEY':secrets.token_urlsafe(64),'DJANGO_ALLOWED_HOSTS':'fictional.onrender.com','DATABASE_URL':'postgres://fake:fake@db.example/demo?sslmode=verify-full'}
        env.update(changes)
        return subprocess.run([sys.executable,'-c',"import django; django.setup(); from django.conf import settings; assert settings.DATABASES['default']['ENGINE']=='django.db.backends.postgresql'; assert settings.SECURE_PROXY_SSL_HEADER == ('HTTP_X_FORWARDED_PROTO','https'); assert settings.SESSION_COOKIE_SECURE"],env=env,capture_output=True,cwd=ROOT)
    def test_valid_profile(self):self.assertEqual(self.check().returncode,0)
    def test_missing_render_marker(self):self.assertNotEqual(self.check(RENDER='').returncode,0)
    def test_no_sqlite(self):self.assertNotEqual(self.check(DATABASE_URL='',DJANGO_DB_PATH='/tmp/demo.sqlite').returncode,0)
    def test_no_debug(self):self.assertNotEqual(self.check(DJANGO_DEBUG='1').returncode,0)
    def test_no_wildcard(self):self.assertNotEqual(self.check(DJANGO_ALLOWED_HOSTS='*').returncode,0)
    def test_no_weak_secret(self):self.assertNotEqual(self.check(DJANGO_SECRET_KEY='short').returncode,0)
    def test_no_insecure_database(self):self.assertNotEqual(self.check(DATABASE_URL='postgres://a:b@db.example/demo?sslmode=disable').returncode,0)
    def test_no_generic_profile(self):self.assertNotEqual(self.check(DJANGO_SETTINGS_MODULE='config.production').returncode,0)
    def test_no_development_profile(self):self.assertNotEqual(self.check(DJANGO_SETTINGS_MODULE='config.settings').returncode,0)
    def test_build_has_no_release_or_seed_commands(self):
        s=(ROOT/'scripts/build-render.sh').read_text()
        for x in ['manage.py migrate','release_database.py','createsuperuser','loaddata']:self.assertNotIn(x,s)
    def test_blueprint_is_only_free_web(self):
        s=(ROOT/'render.yaml').read_text()
        self.assertEqual(s.count('type: web'),1);self.assertIn('plan: free',s);self.assertNotIn('databases:',s);self.assertNotIn('type: cron',s);self.assertIn('autoDeployTrigger: off',s)
    def test_start_has_single_worker_and_platform_port(self):
        s=(ROOT/'scripts/start-render.sh').read_text();self.assertIn('${PORT:-10000}',s);self.assertIn('--workers 1',s)
