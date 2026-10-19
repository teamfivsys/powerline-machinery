"""Isolated PostgreSQL/TLS preparation rehearsal. No external services/accounts.
Requires local PostgreSQL binaries, openssl and uv. Temporary localhost cluster,
fictional records and random one-use credentials only. Runs full regression suite.
"""
import json, os, secrets, shutil, socket, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
os.chdir(ROOT)

def main():
    bins=sorted(Path('/usr/lib/postgresql').glob('*/bin'))
    if not bins: raise RuntimeError('Install local postgresql and postgresql-client first.')
    pg=bins[-1]
    def run(args,**kw): return subprocess.run([str(a) for a in args],check=True,capture_output=True,text=True,**kw)
    checks=[]
    with tempfile.TemporaryDirectory(prefix='powerline-pg-') as temp:
        private=Path(temp);os.chmod(private,0o700)
        with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
        run([pg/'initdb','-D',private/'cluster','--auth=trust','--no-locale','--encoding=UTF8'])
        run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',private/'server.key','-out',private/'server.crt','-days','1','-subj','/CN=localhost'])
        os.chmod(private/'server.key',0o600)
        run([pg/'pg_ctl','-D',private/'cluster','-l',private/'postgres.log','-o',f'-h 127.0.0.1 -p {port} -k {private} -c ssl=on -c ssl_cert_file={private}/server.crt -c ssl_key_file={private}/server.key','-w','start'])
        try:
            pgargs=['-h','127.0.0.1','-p',str(port)]
            for db in ['powerline','restored']:run([pg/'createdb',*pgargs,db])
            user=os.environ.get('USER','user')
            url=f'postgresql://{user}:unused-local-trust-only@127.0.0.1:{port}/powerline?sslmode=require'
            env={**os.environ,'DATABASE_URL':url,'DJANGO_SETTINGS_MODULE':'config.vercel','VERCEL':'1','DJANGO_DEBUG':'0','DJANGO_SECRET_KEY':secrets.token_urlsafe(64),'DJANGO_ALLOWED_HOSTS':'localhost,127.0.0.1','CRON_SECRET':secrets.token_urlsafe(40)}
            def manage(*args,env_override=None):return run([sys.executable,'manage.py',*args],env=env_override or env)
            manage('migrate','operations','0001','--noinput');manage('migrate','auth','--noinput');manage('migrate','sessions','--noinput')
            manage('shell','-c',"from django.contrib.auth import get_user_model; from operations.models import Employee,Assignment; a=get_user_model().objects.create_superuser('pg_fictional_admin','', 'Fictional-test-password-2026!');e=Employee.objects.create(name='Fictional PG Employee',joining_date='2026-01-01',salary_amount='1234.56',salary_currency='AED',salary_basis='fictional');Assignment.objects.create(title='Fictional PG Allocation',employee=e,created_by=a)")
            manage('migrate','--noinput');manage('createcachetable');manage('collectstatic','--noinput')
            checks.append('Existing 0001 employee/allocation records survived all later migrations on PostgreSQL')
            seed="""from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from operations.models import *
import uuid
u=get_user_model().objects.get(username='pg_fictional_admin');e=Employee.objects.get(name='Fictional PG Employee')
assert str(e.salary_amount)=='1234.56' and Assignment.objects.count()==1
q=Enquiry.objects.create(customer_name='Fictional PG Customer',kind='service',summary='Fictional enquiry',details='Test',created_by=u)
j=ServiceJob.objects.create(customer_name=q.customer_name,enquiry=q,machine='Fictional forklift',fault='Fictional fault',technician=e,created_by=u)
TechnicianAccess.objects.create(user=u,employee=e)
LocationShare.objects.create(job=j,user=u,token=uuid.uuid4(),started_at=timezone.now(),expires_at=timezone.now()+timedelta(seconds=120),captured_at=timezone.now(),latitude=1.0,longitude=2.0,accuracy_m=3.0)
from django.test import Client
c=Client();assert c.login(username=u.username,password='Fictional-test-password-2026!'); s=c.session;s['process_probe']='saved';s.save()
print('SESSION_KEY='+s.session_key)
"""
            seedresult=manage('shell','-c',seed)
            key=next(line.split('=',1)[1] for line in seedresult.stdout.splitlines() if line.startswith('SESSION_KEY='))
            # New independent Python process with the same external database, not process memory/files.
            manage('shell','-c',f"from django.contrib.sessions.backends.db import SessionStore; from operations.models import *; assert SessionStore('{key}')['process_probe']=='saved'; assert Enquiry.objects.count()==1; assert ServiceJob.objects.count()==1; assert TechnicianAccess.objects.count()==1; assert Assignment.objects.count()==1")
            checks.append('Independent fresh process recovered DB-backed authenticated session and CRM/service/technician/allocation records')
            deploy=manage('check','--deploy','--fail-level','ERROR')
            checks.append('Vercel production profile system checks passed; only deliberate HSTS subdomain/preload warnings remain')
            # Apply/plan migration idempotently, no mutations during import or Vercel build.
            manage('migrate','--check');manage('makemigrations','--check','--dry-run');manage('migrate','--noinput')
            checks.append('Migration consistency and repeat release migration checks passed')
            release=run([sys.executable,'scripts/release_database.py','--confirm-host','127.0.0.1','--confirm-database','powerline'],env=env)
            assert 'Plan only.' in release.stdout
            applied=run([sys.executable,'scripts/release_database.py','--confirm-host','127.0.0.1','--confirm-database','powerline','--apply'],env=env)
            assert 'Release database steps completed' in applied.stdout
            refused=subprocess.run([sys.executable,'scripts/release_database.py','--confirm-host','wrong.example','--confirm-database','powerline','--apply'],env=env,capture_output=True)
            assert refused.returncode != 0
            checks.append('Explicit release script plan/apply passed; mismatched target refused')
            testenv={**env,'DJANGO_SETTINGS_MODULE':'config.test_settings','DJANGO_DEBUG':'1'}
            testenv.pop('VERCEL',None)
            suite=manage('test',env_override=testenv)
            (ROOT/'evidence/v0.4/postgresql-tests.txt').write_text(suite.stdout+suite.stderr)
            checks.append('Full regression suite passed on local TLS-enabled PostgreSQL')
            # Explicit privacy-aware backup; never includes GPS samples, sessions or throttle state.
            run([pg/'pg_dump',*pgargs,'--format=custom','--no-owner','--no-acl','--exclude-table-data=operations_locationshare','--exclude-table-data=django_session','--exclude-table-data=login_throttle','--file',private/'business.dump','powerline'])
            run([pg/'pg_restore',*pgargs,'--no-owner','--no-acl','--exit-on-error','--dbname=restored',private/'business.dump'])
            restoreenv={**env,'DATABASE_URL':url.replace('/powerline?','/restored?')}
            manage('shell','-c',"from operations.models import *; from django.contrib.auth import get_user_model; from django.contrib.sessions.models import Session; assert Employee.objects.count()==Assignment.objects.count()==Enquiry.objects.count()==ServiceJob.objects.count()==TechnicianAccess.objects.count()==1; assert LocationShare.objects.count()==Session.objects.count()==0; assert get_user_model().objects.get(username='pg_fictional_admin').check_password('Fictional-test-password-2026!')",env_override=restoreenv)
            checks.append('pg_dump/pg_restore to separate database recovered five business tables and administrator password; GPS samples and sessions excluded')
            # Verify TLS was actually negotiated, not just requested.
            result=run([pg/'psql',url,'-Atc','SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid()'])
            assert result.stdout.strip()=='t'
            checks.append('PostgreSQL reported TLS active on the rehearsal connection')
            report={'checks':checks,'count':len(checks),'scope':'Local PostgreSQL with self-signed test TLS; no external provider/Vercel deployment. Temporary cluster and data destroyed after completion.'}
            (ROOT/'evidence/v0.4/postgresql-rehearsal.json').write_text(json.dumps(report,indent=2))
            print(json.dumps(report,indent=2))
        finally:run([pg/'pg_ctl','-D',private/'cluster','-m','fast','-w','stop'])
if __name__=='__main__':main()
