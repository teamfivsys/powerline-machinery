from datetime import date
from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from .models import Employee, Assignment, AuditEvent

class OperationsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.admin = User.objects.create_superuser("test_admin", "", "FictionalTestPass!842")
        cls.operator = User.objects.create_user("test_operator", password="FictionalTestPass!521")
        cls.employee = Employee.objects.create(name="Fictional Staff", joining_date=date(2026, 1, 12), salary_amount=Decimal("4321.67"), salary_currency="AED", salary_basis="monthly")
    def setUp(self): cache.clear()
    def employee_data(self, **extra):
        return {"name": "Example Staff", "joining_date": "2026-02-15", "salary_amount": "2876.54", "salary_currency": "inr", "salary_basis": "monthly", **extra}
    def test_all_business_routes_require_login(self):
        for url in ["/", "/employees/", "/employees/new/", f"/employees/{self.employee.pk}/edit/", "/assignments/", "/assignments/new/", "/modules/crm/", "/modules/maintenance/", "/modules/field-tracking/"]:
            with self.subTest(url=url): self.assertEqual(self.client.get(url).status_code, 302)
    def test_admin_create_employee_and_reopen(self):
        self.client.force_login(self.admin)
        response = self.client.post("/employees/new/", self.employee_data())
        self.assertRedirects(response, "/employees/")
        saved = Employee.objects.get(name="Example Staff")
        self.assertEqual(saved.salary_amount, Decimal("2876.54"))
        self.assertEqual(saved.salary_currency, "INR")
        self.assertEqual(saved.joining_date, date(2026, 2, 15))
        response = self.client.get(f"/employees/{saved.pk}/edit/")
        self.assertContains(response, "2876.54")
        self.assertEqual(AuditEvent.objects.get().action, "employee_created")
    def test_admin_update_employee(self):
        self.client.force_login(self.admin)
        self.client.post(f"/employees/{self.employee.pk}/edit/", self.employee_data(name="Changed Staff"))
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.name, "Changed Staff")
        self.assertEqual(Employee.objects.count(), 1)
        self.assertEqual(AuditEvent.objects.get().action, "employee_updated")
    def test_negative_salary_rejected(self):
        self.client.force_login(self.admin)
        response = self.client.post("/employees/new/", self.employee_data(salary_amount="-1"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "greater than or equal to 0")
        self.assertEqual(Employee.objects.count(), 1)
    def test_invalid_currency_rejected(self):
        self.client.force_login(self.admin)
        response = self.client.post("/employees/new/", self.employee_data(salary_currency="123"))
        self.assertContains(response, "three-letter currency")
        self.assertEqual(Employee.objects.count(), 1)
    def test_invalid_date_rejected(self):
        self.client.force_login(self.admin)
        response = self.client.post("/employees/new/", self.employee_data(joining_date="2026-02-31"))
        self.assertContains(response, "Enter a valid date")
        self.assertEqual(Employee.objects.count(), 1)
    def test_required_fields_rejected(self):
        self.client.force_login(self.admin)
        self.client.post("/employees/new/", {"name": "Only name"})
        self.assertEqual(Employee.objects.count(), 1)
    def test_operator_cannot_see_salary_or_dates(self):
        self.client.force_login(self.operator)
        response = self.client.get("/employees/")
        self.assertContains(response, "Fictional Staff")
        self.assertNotContains(response, "4321.67")
        self.assertNotContains(response, "AED")
        self.assertNotContains(response, "12 Jan 2026")
    def test_operator_cannot_get_or_post_any_employee_form(self):
        self.client.force_login(self.operator)
        for url in ["/employees/new/", f"/employees/{self.employee.pk}/edit/"]:
            self.assertEqual(self.client.get(url).status_code, 403)
            self.assertEqual(self.client.post(url, self.employee_data()).status_code, 403)
        self.assertEqual(Employee.objects.count(), 1)
    def test_assignment_persistence_and_update(self):
        self.client.force_login(self.operator)
        response = self.client.post("/assignments/new/", {"title": "Test allocation", "employee": self.employee.pk, "description": "Fictional instructions"})
        self.assertRedirects(response, "/assignments/")
        item = Assignment.objects.get()
        self.assertEqual(item.employee_id, self.employee.pk)
        self.assertEqual(item.created_by_id, self.operator.pk)
        self.assertContains(self.client.get("/assignments/"), "Test allocation")
        self.assertContains(self.client.get(f"/assignments/{item.pk}/edit/"), "Fictional instructions")
        self.client.post(f"/assignments/{item.pk}/edit/", {"title": "Revised allocation", "employee": self.employee.pk, "description": "Updated"})
        item.refresh_from_db()
        self.assertEqual(item.title, "Revised allocation")
        self.assertEqual(AuditEvent.objects.count(), 2)
    def test_invalid_assignee_rejected(self):
        self.client.force_login(self.admin)
        self.client.post("/assignments/new/", {"title": "Bad assignee", "employee": 999999})
        self.assertEqual(Assignment.objects.count(), 0)
    def test_salary_absent_from_assignment_views(self):
        self.client.force_login(self.operator)
        for url in ["/", "/assignments/", "/assignments/new/"]:
            self.assertNotContains(self.client.get(url), "4321.67")
    def test_csrf_required_for_login(self):
        c = Client(enforce_csrf_checks=True)
        self.assertEqual(c.post("/login/", {"username": "test_admin", "password": "wrong"}).status_code, 403)
    def test_csrf_required_for_mutation(self):
        c = Client(enforce_csrf_checks=True); c.force_login(self.admin)
        self.assertEqual(c.post("/employees/new/", self.employee_data()).status_code, 403)
    def test_password_hashed(self):
        self.assertNotEqual(self.admin.password, "FictionalTestPass!842")
        self.assertTrue(self.admin.password.startswith("pbkdf2_sha256$"))
    def test_login_and_logout(self):
        response = self.client.post("/login/", {"username": "test_admin", "password": "FictionalTestPass!842"})
        self.assertRedirects(response, "/")
        self.assertEqual(self.client.get("/logout/").status_code, 405)
        self.assertRedirects(self.client.post("/logout/"), "/login/")
        self.assertEqual(self.client.get("/").status_code, 302)
    def test_bad_login_generic_error(self):
        r = self.client.post("/login/", {"username": "nonexistent", "password": "wrong"})
        self.assertContains(r, "Please enter a correct username and password")
    def test_login_throttle(self):
        # Seed counters to avoid ten expensive password hashes in this test.
        import hashlib
        key = "login-ip:" + hashlib.sha256(b"127.0.0.1").hexdigest()
        cache.set(key, 10, 900)
        self.assertEqual(self.client.post("/login/", {"username": "test_admin", "password": "wrong"}).status_code, 429)
    def test_login_failure_increments_counters(self):
        import hashlib
        self.client.post("/login/", {"username": "nonexistent", "password": "wrong"})
        key = "login-ip:" + hashlib.sha256(b"127.0.0.1").hexdigest()
        self.assertEqual(cache.get(key), 1)
    def test_external_redirect_not_followed(self):
        r = self.client.post("/login/?next=https://evil.example/", {"username": "test_admin", "password": "FictionalTestPass!842"})
        self.assertRedirects(r, "/")
    def test_xss_escaped(self):
        self.employee.name = '<script>alert("x")</script>'; self.employee.save()
        self.client.force_login(self.admin)
        r = self.client.get("/employees/")
        self.assertNotContains(r, '<script>alert("x")</script>')
        self.assertContains(r, "&lt;script&gt;")
    def test_pending_modules_are_not_claimed_complete(self):
        self.client.force_login(self.admin)
        for slug in ["crm", "maintenance"]:
            self.assertContains(self.client.get(f"/modules/{slug}/"), "Basic workflow available")
        self.assertContains(self.client.get("/modules/field-tracking/"), "Foreground tracking available")
        self.assertEqual(self.client.get("/modules/unknown/").status_code, 404)
    def test_private_response_security_headers(self):
        self.client.force_login(self.admin)
        r = self.client.get("/employees/")
        self.assertEqual(r["Cache-Control"], "no-store, private")
        self.assertIn("script-src 'none'", r["Content-Security-Policy"])
        self.assertEqual(r["X-Frame-Options"], "DENY")
    def test_disabled_account_cannot_login(self):
        self.operator.is_active = False; self.operator.save()
        self.client.post("/login/", {"username": "test_operator", "password": "FictionalTestPass!521"})
        self.assertEqual(self.client.get("/").status_code, 302)
    def test_no_delete_route(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.post(f"/employees/{self.employee.pk}/delete/").status_code, 404)
        self.assertEqual(Employee.objects.count(), 1)
