"""Local-only real-browser temporary-password replacement regression; fictional account."""
import os, json, secrets, socket, subprocess, tempfile, time, urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
os.chdir(ROOT)
with tempfile.TemporaryDirectory(prefix='powerline-account-smoke-') as tmp:
    old=secrets.token_urlsafe(32); new=secrets.token_urlsafe(32)
    env={**{k:v for k,v in os.environ.items() if k not in ('DATABASE_URL','VERCEL','RENDER')},'DJANGO_SETTINGS_MODULE':'config.settings','DJANGO_DEBUG':'1','DJANGO_SECRET_KEY':secrets.token_urlsafe(64),'DJANGO_DB_PATH':tmp+'/app.sqlite3'}
    def manage(*args): return subprocess.run(['uv','run','--frozen','python','manage.py',*args],env=env,check=True,capture_output=True,text=True)
    manage('migrate','--noinput');manage('createcachetable');manage('collectstatic','--noinput')
    manage('shell','-c',"from django.contrib.auth import get_user_model; from operations.models import AccountSecurity; u=get_user_model().objects.create_user('fictional_recovered',password=%r); AccountSecurity.objects.create(user=u)" % old)
    with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
    base=f'http://127.0.0.1:{port}'
    server=subprocess.Popen(['uv','run','--frozen','python','manage.py','runserver','--noreload',f'127.0.0.1:{port}'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    checks=[]
    try:
        for _ in range(80):
            try:urllib.request.urlopen(base+'/login/',timeout=1);break
            except Exception:time.sleep(.2)
        else:raise RuntimeError('Server not ready')
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True);page=browser.new_page(viewport={'width':390,'height':844})
            page.goto(base+'/login/');page.get_by_label('Username').fill('fictional_recovered');page.get_by_label('Password',exact=True).fill(old);page.get_by_role('button',name='Sign in').click();page.wait_for_url(base+'/password/change/')
            checks.append('Temporary-password sign-in redirects to mandatory replacement')
            page.goto(base+'/assignments/');page.wait_for_url(base+'/password/change/');checks.append('Direct operational navigation cannot bypass replacement')
            page.locator('#id_old_password').fill(old);page.locator('#id_new_password1').fill(old);page.locator('#id_new_password2').fill(old);page.get_by_role('button',name='Change password').click()
            assert 'Choose a different password' in page.inner_text('main');checks.append('Reusing the temporary password leaves replacement gate in place')
            page.locator('#id_old_password').fill(old);page.locator('#id_new_password1').fill(new);page.locator('#id_new_password2').fill(new);page.get_by_role('button',name='Change password').click();page.wait_for_url(base+'/');checks.append('Replacement succeeds through real CSRF form and preserves current login')
            page.goto(base+'/password/change/');assert page.evaluate('document.documentElement.scrollWidth <= innerWidth');page.screenshot(path=str(ROOT/'artifacts/password-change-mobile.png'),full_page=True);checks.append('390px password-change page fits viewport')
            page.get_by_role('button',name='Sign out').click();page.wait_for_url(base+'/login/')
            page.get_by_label('Username').fill('fictional_recovered');page.get_by_label('Password',exact=True).fill(new);page.get_by_role('button',name='Sign in').click();page.wait_for_url(base+'/');checks.append('New password signs in after POST logout')
            browser.close()
        report={'result':'passed','checks':checks,'scope':'Local SQLite and Chromium mobile emulation; no actual user/device, email or cloud service.'}
        (ROOT/'evidence/v0.6/account-browser.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
    finally:
        server.terminate()
        try:server.wait(timeout=10)
        except subprocess.TimeoutExpired:server.kill();server.wait()
