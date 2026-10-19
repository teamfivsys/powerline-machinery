from getpass import getpass
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
class Command(BaseCommand):
    help = "Provision a non-administrator operator; no email sent. Client permissions are provisional."
    def add_arguments(self, parser): parser.add_argument("username")
    def handle(self, *args, **opts):
        User = get_user_model()
        if User.objects.filter(username=opts["username"]).exists(): raise CommandError("Username already exists; no account changed.")
        user = User(username=opts["username"])
        password = getpass("New password: ")
        if password != getpass("Confirm password: "): raise CommandError("Passwords do not match.")
        try: validate_password(password, user)
        except ValidationError as e: raise CommandError("; ".join(e.messages))
        user.set_password(password); user.save()
        self.stdout.write(self.style.SUCCESS("Operator created. Share access securely, not in source code."))
