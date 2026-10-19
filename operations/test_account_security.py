from datetime import timedelta
from io import StringIO
from unittest.mock import patch
import uuid
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command, CommandError
from django.db import connection
from django.test import TestCase, Client
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from .models import AccountSecurity, AuditEvent, Employee, Assignment, LocationShare, ServiceJob, TechnicianAccess

OLD = "FictionalCredential!728431"
NEW = "ReplacementExample!924783"
FINAL = "PersonalExample!3748291"

class AccountSecurityTests(TestCase):
    def setUp(self):
        cache.clear()
        U=get_user_model()
        self.admin=U.objects.create_superuser("security_admin", "", OLD)
        self.user=U.objects.create_user("fictional_tech", password=OLD)
        self.employee=Employee.objects.create(name="Fictional Tech", joining_date="2026-01-01", salary_amount="1234.56", salary_currency="INR", salary_basis="fictional")
        TechnicianAccess.objects.create(user=self.user, employee=self.employee)
        self.job=ServiceJob.objects.create(customer_name="Fictional Customer",machine="Fictional Forklift",fault="Test fault",technician=self.employee,created_by=self.admin)
        Assignment.objects.create(title="Fictional allocation",employee=self.employee,created_by=self.admin)
    def share(self):
        return LocationShare.objects.create(job=self.job,user=self.user,token=uuid.uuid4(),started_at=timezone.now(),expires_at=timezone.now()+timedelta(seconds=120))
    def recover(self, password=NEW):
        output=StringIO()
        with patch("operations.management.commands.recover_account.getpass",side_effect=[password,password]):
            call_command("recover_account", self.user.username, identity_verified=True, stdout=output)
        return output.getvalue()
    def test_recovery_requires_independent_verification(self):
        with self.assertRaises(CommandError): call_command("recover_account",self.user.username)
        self.user.refresh_from_db();self.assertTrue(self.user.check_password(OLD))
        self.assertFalse(AccountSecurity.objects.exists())
    def test_recovery_changes_password_not_roles_and_clears_sharing(self):
        self.share();text=self.recover();self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(NEW));self.assertFalse(self.user.is_superuser);self.assertFalse(self.user.is_staff)
        self.assertTrue(self.user.is_active);self.assertEqual(TechnicianAccess.objects.count(),1)
        self.assertFalse(LocationShare.objects.exists());self.assertTrue(AccountSecurity.objects.get(user=self.user).must_change_password)
        self.assertNotIn(NEW,text);self.assertEqual(AuditEvent.objects.get().action,"account_recovered_terminal")
    def test_recovery_invalidates_old_sessions_and_password(self):
        self.client.login(username=self.user.username,password=OLD);self.recover()
        self.assertRedirects(self.client.get("/my-service/"),"/login/?next=/my-service/",fetch_redirect_response=False)
        self.assertFalse(self.client.login(username=self.user.username,password=OLD))
        self.assertTrue(self.client.login(username=self.user.username,password=NEW))
        self.assertRedirects(self.client.get("/my-service/"),"/password/change/",fetch_redirect_response=False)
    def test_required_change_blocks_gets_and_writes_without_mutating_records(self):
        AccountSecurity.objects.create(user=self.user);self.client.force_login(self.user)
        for url in ["/", "/employees/", "/assignments/new/", "/crm/", "/dispatcher/",f"/my-service/{self.job.pk}/location/start/"]:
            self.assertEqual(self.client.get(url).url,"/password/change/")
            self.assertEqual(self.client.post(url,{"consent":"foreground"}).url,"/password/change/")
        self.assertFalse(LocationShare.objects.exists());self.assertEqual(Assignment.objects.count(),1)
    def test_required_change_is_csrf_protected(self):
        AccountSecurity.objects.create(user=self.user);c=Client(enforce_csrf_checks=True);c.force_login(self.user)
        self.assertEqual(c.post("/password/change/",{"old_password":OLD,"new_password1":NEW,"new_password2":NEW}).status_code,403)
        self.assertTrue(AccountSecurity.objects.get().must_change_password)
    def test_successful_password_change_keeps_current_login_invalidates_other(self):
        AccountSecurity.objects.create(user=self.user);self.share()
        self.client.login(username=self.user.username,password=OLD);other=Client();other.login(username=self.user.username,password=OLD)
        self.assertRedirects(self.client.post("/password/change/",{"old_password":OLD,"new_password1":NEW,"new_password2":NEW}),"/")
        self.assertFalse(AccountSecurity.objects.get().must_change_password);self.assertFalse(LocationShare.objects.exists())
        self.assertEqual(self.client.get("/my-service/").status_code,200)
        self.assertEqual(other.get("/my-service/").status_code,302)
    def test_same_temporary_password_cannot_clear_gate(self):
        AccountSecurity.objects.create(user=self.user);self.client.force_login(self.user)
        response=self.client.post("/password/change/",{"old_password":OLD,"new_password1":OLD,"new_password2":OLD})
        self.assertContains(response,"Choose a different password");self.assertTrue(AccountSecurity.objects.get().must_change_password)
    def test_weak_or_mismatched_recovery_does_not_mutate(self):
        for passwords in [["short","short"],[NEW,FINAL]]:
            with patch("operations.management.commands.recover_account.getpass",side_effect=passwords),self.assertRaises(CommandError):
                call_command("recover_account",self.user.username,identity_verified=True)
        self.user.refresh_from_db();self.assertTrue(self.user.check_password(OLD));self.assertFalse(AccountSecurity.objects.exists())
    def test_inactive_account_not_reactivated(self):
        self.user.is_active=False;self.user.save()
        with self.assertRaises(CommandError): call_command("recover_account",self.user.username,identity_verified=True)
        self.user.refresh_from_db();self.assertFalse(self.user.is_active)
    def test_same_recovery_password_refused(self):
        with self.assertRaises(CommandError): self.recover(OLD)
        self.assertFalse(AccountSecurity.objects.exists())
    def test_logout_post_clears_location_but_get_does_not(self):
        self.share();self.client.force_login(self.user)
        self.assertEqual(self.client.get("/logout/").status_code,405);self.assertTrue(LocationShare.objects.exists())
        self.assertEqual(self.client.post("/logout/").status_code,302);self.assertFalse(LocationShare.objects.exists())
    def test_new_operator_enforces_replacement_and_validates_username(self):
        with patch("operations.management.commands.create_operator.getpass",side_effect=[NEW,NEW]):
            call_command("create_operator","new_operator",stdout=StringIO())
        u=get_user_model().objects.get(username="new_operator");self.assertTrue(AccountSecurity.objects.get(user=u).must_change_password)
        with patch("operations.management.commands.create_operator.getpass",side_effect=[NEW,NEW]),self.assertRaises(CommandError):
            call_command("create_operator","invalid username",stdout=StringIO())
        self.assertFalse(get_user_model().objects.filter(username="invalid username").exists())
    def test_new_technician_enforces_replacement(self):
        TechnicianAccess.objects.all().delete()
        with patch("operations.management.commands.create_technician.getpass",side_effect=[NEW,NEW]):
            call_command("create_technician","new_tech",self.employee.pk,stdout=StringIO())
        u=get_user_model().objects.get(username="new_tech");self.assertTrue(AccountSecurity.objects.get(user=u).must_change_password)
        self.assertEqual(u.technician_access.employee_id,self.employee.pk)
    def test_legacy_accounts_are_not_silently_gated(self):
        self.client.force_login(self.user);self.assertEqual(self.client.get("/my-service/").status_code,200)
        self.assertFalse(AccountSecurity.objects.exists())
    def test_operational_views_do_not_select_salary_columns(self):
        self.client.force_login(self.user)
        for url in ["/", "/assignments/", "/assignments/new/"]:
            with CaptureQueriesContext(connection) as ctx: response=self.client.get(url)
            self.assertEqual(response.status_code,200)
            for query in ctx:
                self.assertNotIn('"salary_amount"',query["sql"])
                self.assertNotIn('"salary_basis"',query["sql"])
    def test_audit_and_page_do_not_expose_passwords(self):
        text=self.recover();self.client.force_login(self.user)
        page=self.client.get("/password/change/").content.decode()
        self.assertNotIn(NEW,text+page+str(list(AuditEvent.objects.values())))

    def test_empty_employee_post_is_bound_and_shows_errors(self):
        self.client.force_login(self.admin)
        self.assertContains(self.client.post("/employees/new/",{}),"This field is required")
    def test_empty_allocation_post_is_bound_and_shows_errors(self):
        self.client.force_login(self.user)
        self.assertContains(self.client.post("/assignments/new/",{}),"This field is required")
