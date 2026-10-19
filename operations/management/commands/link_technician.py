"""Local administrator command. Never infers identity from names or grants superuser."""
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db import transaction
from operations.models import Employee, TechnicianAccess, LocationShare
class Command(BaseCommand):
    help="Explicitly link an existing active non-superuser login to an employee ID; no password changes."
    def add_arguments(self,parser):
        parser.add_argument("username");parser.add_argument("employee_id",type=int)
    def handle(self,*args,**opts):
        try:
            user=get_user_model().objects.get(username=opts["username"],is_active=True,is_superuser=False)
            employee=Employee.objects.only("id","name").get(pk=opts["employee_id"])
        except (get_user_model().DoesNotExist,Employee.DoesNotExist):raise CommandError("Active non-administrator login or employee was not found.")
        if TechnicianAccess.objects.filter(employee=employee).exclude(user=user).exists():raise CommandError("Employee is already linked to a different login.")
        with transaction.atomic():
            LocationShare.objects.filter(user=user).delete()
            TechnicianAccess.objects.update_or_create(user=user,defaults={"employee":employee})
        self.stdout.write(self.style.SUCCESS("Technician mapping saved. No password or administrator permission changed."))
