"""Local-only production-profile/TLS proxy/WSGI and SQLite recovery rehearsal.
Creates only fictional data and temporary credentials/certificates. No hosting signup,
external requests or source database access. Requires openssl on Linux; dependencies
are locked in uv.lock. Run: uv run --frozen python scripts/rehearse_production.py
"""
import http.client
from http.cookiejar import CookieJar
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import secrets
import socket
import ssl
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
ROOT=Path(__file__).resolve().parents[1]
os.chdir(ROOT)

def free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1',0)); return s.getsockname()[1]

def main():
    checks=[]; expected_warnings=[]
    with tempfile.TemporaryDirectory(prefix='powerline-production-rehearsal-') as tmp:
        private=Path(tmp);os.chmod(private,0o700)
        env={**{k:v for k,v in os.environ.items() if k not in ('DATABASE_URL','VERCEL')},'DJANGO_SETTINGS_MODULE':'config.production','DJANGO_DEBUG':'0','DJANGO_SECRET_KEY':secrets.token_urlsafe(64),'DJANGO_ALLOWED_HOSTS':'localhost,127.0.0.1','DJANGO_DB_PATH':str(private/'app.sqlite3'),'DJANGO_TRUST_HTTPS_PROXY':'1'}
        def manage(*args):
            return subprocess.run([sys.executable,'manage.py',*args],env=env,capture_output=True,text=True,check=True)
        manage('migrate','--noinput');manage('createcachetable');manage('collectstatic','--noinput')
        deploy=manage('check','--deploy','--fail-level','ERROR')
        expected_warnings=re.findall(r'security\.W\d+',deploy.stderr)
        assert set(expected_warnings)=={'security.W005','security.W021'},deploy.stderr
        checks.append('Production checks: no errors; only documented HSTS subdomain/preload warnings W005/W021')
        admin=secrets.token_urlsafe(24);operator=secrets.token_urlsafe(24)
        seed="""from django.contrib.auth import get_user_model
from operations.models import Employee,Assignment,Enquiry,ServiceJob,TechnicianAccess,LocationShare
from django.utils import timezone
from datetime import timedelta
import uuid
U=get_user_model();a=U.objects.create_superuser('rehearsal_admin','',%r);o=U.objects.create_user('rehearsal_operator',password=%r)
e=Employee.objects.create(name='Fictional Recovery Employee',joining_date='2026-01-01',salary_amount='56789.12',salary_currency='AED',salary_basis='fictional test only')
Assignment.objects.create(title='Fictional Recovery Allocation',employee=e,created_by=a)
q=Enquiry.objects.create(customer_name='Fictional Recovery Customer',kind='service',summary='Fictional service recovery',details='Test details',created_by=a)
j=ServiceJob.objects.create(customer_name='Fictional Recovery Customer',enquiry=q,machine='Fictional recovery forklift',fault='Test fault',technician=e,created_by=a)
TechnicianAccess.objects.create(user=o,employee=e)
LocationShare.objects.create(job=j,user=o,token=uuid.uuid4(),started_at=timezone.now(),expires_at=timezone.now()+timedelta(seconds=120),captured_at=timezone.now(),latitude=0.123456,longitude=0.654321,accuracy_m=12.3)
""" % (admin,operator)
        manage('shell','-c',seed)
        upstream=free_port()
        log=open(private/'wsgi.log','w')
        def start_wsgi():
            process=subprocess.Popen([str(ROOT/'.venv/bin/gunicorn'),'config.wsgi:application','--bind',f'127.0.0.1:{upstream}','--workers','1','--access-logfile','/dev/null','--error-logfile','-','--forwarded-allow-ips',''],env=env,stdout=log,stderr=log)
            for _ in range(80):
                if process.poll() is not None: raise RuntimeError('WSGI server failed to start')
                try:
                    with socket.create_connection(('127.0.0.1',upstream),timeout=.2): return process
                except OSError:time.sleep(.1)
            process.terminate();process.wait(timeout=10);raise RuntimeError('WSGI start deadline')
        process=start_wsgi()
        subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(private/'tls.key'),'-out',str(private/'tls.crt'),'-days','1','-subj','/CN=localhost'],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        class Proxy(BaseHTTPRequestHandler):
            protocol_version='HTTP/1.1'
            def log_message(self,*args): pass
            def handle_request(self):
                conn=http.client.HTTPConnection('127.0.0.1',upstream,timeout=10)
                hop={'connection','transfer-encoding','keep-alive','proxy-authenticate','proxy-authorization','te','trailer','upgrade','x-forwarded-proto','forwarded','x-forwarded-host','x-forwarded-for'}
                headers={k:v for k,v in self.headers.items() if k.lower() not in hop}
                headers['X-Forwarded-Proto']='https';headers['Connection']='close'
                size=int(self.headers.get('Content-Length','0')); body=self.rfile.read(size) if size else None
                try:
                    conn.request(self.command,self.path,body=body,headers=headers);r=conn.getresponse();data=r.read()
                    self.send_response(r.status)
                    for k,v in r.getheaders():
                        if k.lower() not in hop|{'content-length','server','date'}:self.send_header(k,v)
                    self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
                finally: conn.close()
            do_GET=handle_request;do_POST=handle_request
        proxy=ThreadingHTTPServer(('127.0.0.1',0),Proxy)
        tls=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);tls.load_cert_chain(private/'tls.crt',private/'tls.key')
        proxy.socket=tls.wrap_socket(proxy.socket,server_side=True)
        thread=threading.Thread(target=proxy.serve_forever,daemon=True);thread.start()
        base=f'https://localhost:{proxy.server_port}'
        ssl_context=ssl._create_unverified_context() # ephemeral self-signed local-only fixture
        def new_browser():
            jar=CookieJar();return urllib.request.build_opener(urllib.request.HTTPSHandler(context=ssl_context),urllib.request.HTTPCookieProcessor(jar)),jar
        from urllib.parse import urlencode
        def request(browser,path,fields=None,headers=None):
            req=urllib.request.Request(base+path,data=urlencode(fields).encode() if fields is not None else None,headers=headers or {})
            try:r=browser.open(req,timeout=10)
            except urllib.error.HTTPError as e:r=e
            data=r.read().decode();return r,data
        def sign_in(username,password):
            browser,jar=new_browser();r,html=request(browser,'/login/');assert r.status==200
            token=re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"',html)[1]
            r,html=request(browser,'/login/',{'csrfmiddlewaretoken':token,'username':username,'password':password},{'Referer':base+'/login/'})
            assert r.status==200 and r.url==base+'/',r.url
            return browser,jar
        try:
            conn=http.client.HTTPConnection('127.0.0.1',upstream);conn.request('GET','/login/',headers={'Host':'localhost'});r=conn.getresponse();assert r.status==301;r.read();conn.close()
            checks.append('Plain HTTP upstream redirects to HTTPS under production profile')
            browser,jar=sign_in('rehearsal_admin',admin)
            session=next(c for c in jar if c.name=='powerline_sessionid')
            assert session.secure and session.has_nonstandard_attr('HttpOnly') and session.get_nonstandard_attr('SameSite')=='Lax'
            assert next(c for c in jar if c.name=='powerline_csrftoken').secure
            checks.append('Real TLS proxy and Gunicorn sign-in issues Secure/HttpOnly/SameSite session and Secure CSRF cookies')
            r,html=request(browser,'/employees/',headers={'X-Forwarded-Proto':'http'})
            assert '56789.12' in html and r.status==200
            assert r.headers['Cache-Control']=='no-store, private' and 'script-src' in r.headers['Content-Security-Policy']
            assert r.headers['Strict-Transport-Security']=='max-age=31536000'
            checks.append('Administrator salary page loads with no-store/CSP/HSTS; proxy overwrites spoofed scheme header')
            css=re.search(r'href="(/static/[^"]+\.css)"',html)[1]
            r,cssbody=request(browser,css);assert r.status==200 and cssbody
            checks.append('WhiteNoise serves hashed collected CSS in production mode')
            r,_=request(browser,'/employees/1/edit/',{'name':'Untrusted CSRF attempt'},{'Referer':base+'/employees/1/edit/'})
            assert r.status==403
            checks.append('Missing-CSRF employee mutation rejected through real production WSGI stack')
            op,_=sign_in('rehearsal_operator',operator)
            r,html=request(op,'/employees/');assert r.status==200 and 'Fictional Recovery Employee' in html and '56789.12' not in html
            r,_=request(op,'/employees/1/edit/');assert r.status==403
            checks.append('Regular operator cannot read salary or directly edit employee over TLS/Gunicorn')
            for path in ['/crm/','/maintenance/','/dispatcher/']:
                r,_=request(op,path);assert r.status==403
            r,html=request(op,'/my-service/');assert r.status==200 and 'Fictional recovery forklift' in html
            r,html=request(browser,'/crm/');assert 'Fictional Recovery Customer' in html
            checks.append('Production WSGI routes preserve CRM/dispatch administrator access and assigned technician job access')
            r,_=request(op,'/employees/',headers={'Host':'untrusted.invalid'});assert r.status==400
            checks.append('Unlisted Host header rejected by production host validation')
            def snapshot(operation,source,dest):
                result=subprocess.run([sys.executable,'scripts/sqlite_snapshot.py',operation,str(source),str(dest)],capture_output=True,text=True,check=True)
                return json.loads(result.stdout)
            backup=snapshot('backup',private/'app.sqlite3',private/'backup.sqlite3')
            restore=snapshot('restore-new',private/'backup.sqlite3',private/'restored.sqlite3')
            assert backup['table_counts']==restore['table_counts'] and restore['mode']=='0o600'
            assert backup['table_counts']['operations_locationshare']==0
            checks.append('Consistent SQLite snapshot restored with eleven table counts matching; active location samples excluded')
            process.terminate();process.wait(timeout=10)
            env['DJANGO_DB_PATH']=str(private/'restored.sqlite3')
            manage('check');process=start_wsgi()
            recovered,_=sign_in('rehearsal_admin',admin)
            r,html=request(recovered,'/employees/');assert r.status==200 and '56789.12' in html
            r,html=request(recovered,'/assignments/');assert 'Fictional Recovery Allocation' in html
            r,html=request(recovered,'/crm/');assert 'Fictional Recovery Customer' in html
            r,html=request(recovered,'/maintenance/');assert 'Fictional recovery forklift' in html
            r,html=request(recovered,'/dispatcher/');assert '0.123456' not in html
            checks.append('Restored WSGI retained login, employee, allocation, CRM, maintenance and mapping; no location coordinates restored')
            report={'result':'passed','checks':checks,'warning_ids':sorted(set(expected_warnings)),'restored_table_counts':restore['table_counts'],'limits':['Loopback-only single-worker Gunicorn and ephemeral self-signed TLS proxy, not an internet host','SQLite only; no production storage or PostgreSQL validation','Fictional records and disposable credentials only; no client data, certificate, account or secret retained','No real client device, concurrency/load, independent penetration test or external backup storage verified']}
            (ROOT/'evidence/v0.3-production-rehearsal.json').write_text(json.dumps(report,indent=2)+'\n')
            print(json.dumps(report,indent=2))
        finally:
            proxy.shutdown();proxy.server_close();thread.join(timeout=5)
            if process.poll() is None:
                process.terminate()
                try:process.wait(timeout=10)
                except subprocess.TimeoutExpired:process.kill();process.wait()
            log.close()
if __name__=='__main__': main()
