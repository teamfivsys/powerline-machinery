"""Isolated local browser smoke; creates fictional data in a temporary database.
Run: uv run --frozen python scripts/browser_smoke.py
Requires: uv run playwright install chromium
No real login or employee data is read. No external service is contacted by the app.
"""
import os, sys, json, secrets, subprocess, tempfile, time, urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
artifacts = ROOT / "artifacts"; artifacts.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(prefix="powerline-smoke-") as temp:
    env = {**{k:v for k,v in os.environ.items() if k not in ("DATABASE_URL","VERCEL")}, "DJANGO_SETTINGS_MODULE": "config.settings", "DJANGO_DEBUG": "1", "DJANGO_SECRET_KEY": secrets.token_urlsafe(64), "DJANGO_DB_PATH": temp + "/test.sqlite3"}
    def cmd(*args): return subprocess.run(["uv", "run", "--frozen", "python", "manage.py", *args], env=env, check=True, capture_output=True, text=True)
    cmd("migrate", "--noinput"); cmd("createcachetable"); cmd("collectstatic", "--noinput")
    admin_password = secrets.token_urlsafe(24)
    operator_password = secrets.token_urlsafe(24)
    create = "from django.contrib.auth import get_user_model; U=get_user_model(); U.objects.create_superuser('smoke_admin','',%r); U.objects.create_user('smoke_operator',password=%r)" % (admin_password, operator_password)
    cmd("shell", "-c", create)
    import socket
    with socket.socket() as sock:
        sock.bind(("127.0.0.1",0));port=sock.getsockname()[1]
    server = subprocess.Popen(["uv", "run", "--frozen", "python", "manage.py", "runserver", "--noreload", "127.0.0.1:"+str(port)], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base="http://127.0.0.1:"+str(port)
    checks=[]
    try:
        for n in range(60):
            try:
                urllib.request.urlopen(base+"/login/", timeout=1); break
            except Exception: time.sleep(.25)
        else: raise RuntimeError("Local server did not become ready")
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True)
            page=browser.new_page(viewport={"width":1440,"height":1000})
            errors=[]
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(base+"/login/")
            page.screenshot(path=str(artifacts/"login-desktop.png"), full_page=True)
            page.get_by_label("Username").fill("smoke_admin")
            page.get_by_label("Password", exact=True).fill(admin_password)
            page.get_by_role("button",name="Sign in").click()
            page.wait_for_url(base+"/"); checks.append("Admin signs in through real CSRF-protected form")
            page.goto(base+"/employees/new/")
            page.get_by_label("Name", exact=False).fill("Fictional Test Employee")
            page.get_by_label("Joining date", exact=False).fill("2026-10-01")
            page.get_by_label("Salary amount", exact=False).fill("2500.50")
            page.get_by_label("Salary currency", exact=False).fill("AED")
            page.get_by_label("Salary basis", exact=False).fill("monthly (test assumption)")
            page.get_by_role("button",name="Save record").click()
            page.wait_for_url(base+"/employees/")
            assert "2500.50" in page.inner_text("main")
            page.reload(); assert "Fictional Test Employee" in page.inner_text("main")
            checks.append("Employee joining/salary record saved and persists after reload")
            page.screenshot(path=str(artifacts/"employees-desktop.png"), full_page=True)
            page.goto(base+"/assignments/new/")
            page.get_by_label("Title", exact=False).fill("Fictional allocation for review")
            page.get_by_label("Employee", exact=False).select_option(label="Fictional Test Employee")
            page.get_by_label("Description", exact=False).fill("Test work instructions. No employee notification is sent.")
            page.get_by_role("button",name="Save record").click()
            page.wait_for_url(base+"/assignments/"); page.reload()
            assert "Fictional allocation for review" in page.inner_text("main")
            checks.append("Allocation saves staff responsibility and persists after reload")
            page.goto(base+"/");page.screenshot(path=str(artifacts/"overview-desktop.png"),full_page=True)
            page.goto(base+"/crm/new/")
            page.get_by_label("Customer name",exact=False).fill("Fictional Forklift Customer")
            page.get_by_label("Contact",exact=False).fill("test@example.invalid")
            page.get_by_label("Kind",exact=False).select_option("service")
            page.get_by_label("Summary",exact=False).fill("Fictional forklift service enquiry")
            page.get_by_label("Details",exact=False).fill("Fictional hydraulic fault for local test only.")
            page.get_by_label("Status",exact=False).select_option("in_progress")
            page.get_by_label("Follow up notes",exact=False).fill("Fictional follow-up recorded")
            page.get_by_role("button",name="Save record").click();page.wait_for_url(base+"/crm/");page.reload()
            assert "Fictional forklift service enquiry" in page.inner_text("main")
            checks.append("CRM create/save/reload persists service enquiry and follow-up")
            page.screenshot(path=str(artifacts/"crm-desktop.png"),full_page=True)
            page.goto(base+"/maintenance/new/")
            page.get_by_label("Customer name",exact=False).fill("Fictional Forklift Customer")
            page.get_by_label("Enquiry",exact=False).select_option(label="ENQ-1: Fictional forklift service enquiry")
            page.get_by_label("Machine",exact=False).fill("Fictional forklift / TEST-01")
            page.get_by_label("Fault",exact=False).fill("Fictional hydraulic fault")
            page.get_by_label("Technician",exact=False).select_option(label="Fictional Test Employee")
            page.get_by_role("button",name="Save record").click();page.wait_for_url(base+"/maintenance/");page.reload()
            assert "Fictional forklift / TEST-01" in page.inner_text("main")
            checks.append("Maintenance links existing employee and Service enquiry; saves and reopens")
            page.screenshot(path=str(artifacts/"maintenance-desktop.png"),full_page=True)
            page.goto(base+"/crm/1/edit/")
            page.get_by_label("Status",exact=False).select_option("closed")
            page.get_by_role("button",name="Save record").click()
            assert "Record the enquiry outcome before closing" in page.inner_text("main")
            page.get_by_label("Closure outcome",exact=False).fill("Fictional service arranged; not payment confirmation")
            page.get_by_role("button",name="Save record").click();page.wait_for_url(base+"/crm/")
            assert "Closed" in page.inner_text("main")
            page.goto(base+"/crm/1/edit/");page.get_by_label("Status",exact=False).select_option("open");page.get_by_role("button",name="Save record").click();page.wait_for_url(base+"/crm/")
            checks.append("CRM closure validation, recorded outcome and reopening work in browser")
            cmd("shell","-c","from django.contrib.auth import get_user_model; from operations.models import Employee,TechnicianAccess; u=get_user_model().objects.create_user('smoke_tech',password=%r);TechnicianAccess.objects.create(user=u,employee=Employee.objects.get(pk=1))" % operator_password)
            tech=browser.new_page(viewport={"width":390,"height":844},is_mobile=True,has_touch=True)
            tech.add_init_script("""window.__locationTestDenied=false;window.__watchCleared=false;
            Object.defineProperty(navigator,'geolocation',{value:{
              watchPosition(success,error){setTimeout(()=>{if(window.__locationTestDenied)error({code:1});else success({coords:{latitude:0.123456,longitude:0.654321,accuracy:12.3},timestamp:Date.now()});},100);return 42;},
              clearWatch(){window.__watchCleared=true;}
            }});""")
            tech.goto(base+"/login/");tech.get_by_label("Username").fill("smoke_tech");tech.get_by_label("Password",exact=True).fill(operator_password);tech.get_by_role("button",name="Sign in").click();tech.wait_for_url(base+"/")
            tech.goto(base+"/my-service/1/")
            assert "Location sharing is off" in tech.inner_text("main")
            tech.get_by_role("button",name="Start location sharing").click()
            expect(tech.locator("#location-state")).to_contain_text("Last position confirmed",timeout=15000)
            page.goto(base+"/dispatcher/");assert "0.123456" in page.inner_text("main")
            checks.append("Synthetic foreground coordinates saved only after Start and visible to admin with timestamp/accuracy")
            assert tech.evaluate("document.documentElement.scrollWidth <= innerWidth")
            tech.screenshot(path=str(artifacts/"technician-mobile.png"),full_page=True)
            page.evaluate("() => {const p=document.createElement('p');p.className='notice';p.textContent='SIMULATED COORDINATES — LOCAL BROWSER TEST, NOT A REAL PERSON';document.querySelector('main').prepend(p);}")
            page.screenshot(path=str(artifacts/"dispatcher-simulated-desktop.png"),full_page=True)
            tech.get_by_role("button",name="Stop sharing",exact=True).click()
            expect(tech.locator("#location-state")).to_have_text("Location sharing is off.")
            page.reload();assert "0.123456" not in page.inner_text("main")
            checks.append("Explicit Stop clears dispatcher location")
            tech.evaluate("window.__locationTestDenied=true")
            tech.get_by_role("button",name="Start location sharing").click()
            expect(tech.locator("#location-state")).to_contain_text("permission denied")
            page.reload();assert "0.123456" not in page.inner_text("main")
            checks.append("Simulated permission denial stops sharing without a location sample")
            tech.get_by_label("Status",exact=False).select_option("completed")
            tech.get_by_label("Work done",exact=False).fill("Fictional inspection and repair complete")
            tech.get_by_role("button",name="Save progress").click();tech.wait_for_url(base+"/my-service/1/")
            assert tech.get_by_label("Status",exact=False).input_value()=="completed"
            assert tech.get_by_role("button",name="Start location sharing").count()==0
            page.goto(base+"/maintenance/");assert "Completed" in page.inner_text("main")
            checks.append("Assigned technician completes job with persisted work; completion removes sharing UI")
            response=tech.goto(base+"/dispatcher/");assert response.status==403
            response=tech.goto(base+"/crm/");assert response.status==403
            checks.append("Technician denied dispatcher and CRM routes")
            tech.close()
            mobile=browser.new_page(viewport={"width":390,"height":844},is_mobile=True,has_touch=True,device_scale_factor=1)
            mobile.goto(base+"/login/")
            mobile.get_by_label("Username").fill("smoke_admin")
            mobile.get_by_label("Password",exact=True).fill(admin_password)
            mobile.get_by_role("button",name="Sign in").click()
            mobile.wait_for_url(base+"/")
            assert mobile.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
            mobile.screenshot(path=str(artifacts/"overview-mobile.png"),full_page=True)
            mobile.goto(base+"/employees/new/")
            assert mobile.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
            mobile.screenshot(path=str(artifacts/"employee-form-mobile.png"),full_page=True)
            checks.append("390px mobile overview/form fit viewport; Chromium mobile emulation, not physical Android")
            page.get_by_role("button",name="Sign out").click();page.wait_for_url(base+"/login/")
            page.get_by_label("Username").fill("smoke_operator")
            page.get_by_label("Password",exact=True).fill(operator_password)
            page.get_by_role("button",name="Sign in").click();page.wait_for_url(base+"/")
            page.goto(base+"/employees/")
            assert "2500.50" not in page.content()
            response=page.goto(base+"/employees/1/edit/");assert response.status == 403
            checks.append("Operator cannot view salary in HTML or open employee editing route")
            assert not errors, errors
            checks.append("No browser page errors observed")
            browser.close()
        report={"result":"passed", "checks":checks,"limitations":["Only local SQLite and Chromium desktop/mobile emulation tested", "All coordinates are simulated fictional fixtures; no physical GPS/device permission tested", "No actual Android/laptop client device, email, internet deployment or load tested"]}
        (artifacts/"browser-smoke.json").write_text(json.dumps(report,indent=2))
        print(json.dumps(report,indent=2))
    finally:
        server.terminate()
        try: server.wait(timeout=10)
        except subprocess.TimeoutExpired: server.kill(); server.wait()
