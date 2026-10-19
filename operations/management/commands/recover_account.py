"""Operator-assisted recovery on the trusted server terminal, not an email reset."""
from getpass import getpass
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from operations.models import AccountSecurity, AuditEvent, LocationShare

class Command(BaseCommand):
    help = "Replace an active account password after out-of-band identity verification. No email or role change."
    def add_arguments(self, parser):
        parser.add_argument("username")
        parser.add_argument("--identity-verified", action="store_true", help="Confirm the operator verified the account holder via an approved independent channel.")
    def handle(self, *args, **options):
        if not options["identity_verified"]:
            raise CommandError("Verify the account holder independently first; then supply --identity-verified. No account changed.")
        try: user = get_user_model().objects.get(username=options["username"], is_active=True)
        except get_user_model().DoesNotExist: raise CommandError("Active account not found. No account changed.")
        password = getpass("Temporary replacement password (not echoed): ")
        if password != getpass("Confirm temporary replacement: "):
            raise CommandError("Passwords do not match. No account changed.")
        try: validate_password(password, user)
        except ValidationError as exc: raise CommandError("; ".join(exc.messages))
        if user.check_password(password): raise CommandError("Choose a different password. No account changed.")
        with transaction.atomic():
            user = get_user_model().objects.select_for_update().get(pk=user.pk)
            if not user.is_active: raise CommandError("Account is now inactive. No account changed.")
            user.set_password(password); user.save(update_fields=["password"])
            AccountSecurity.objects.update_or_create(user=user, defaults={"must_change_password": True})
            LocationShare.objects.filter(user=user).delete()
            AuditEvent.objects.create(actor=None, action="account_recovered_terminal", object_type="account", object_id=user.pk)
        self.stdout.write(self.style.SUCCESS("Password replaced; existing authenticated sessions invalidated and location shares removed. The account must change its password on next sign-in. No email sent; roles and active status unchanged."))
