"""Interactive, local administrator provisioning; never ships a default password."""
from getpass import getpass
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from operations.models import Employee, TechnicianAccess
class Command(BaseCommand):
    help='Create a non-administrator technician login and explicitly link an employee. Password is requested privately.'
    def add_arguments(self,p):p.add_argument('username');p.add_argument('employee_id',type=int)
    def handle(self,*args,**opts):
        U=get_user_model()
        if U.objects.filter(username=opts['username']).exists():raise CommandError('Login already exists. Use link_technician for an existing login.')
        try:e=Employee.objects.only('id').get(pk=opts['employee_id'])
        except Employee.DoesNotExist:raise CommandError('Employee not found.')
        if TechnicianAccess.objects.filter(employee=e).exists():raise CommandError('Employee already has a linked login.')
        user=U(username=opts['username'],is_staff=False,is_superuser=False)
        password=getpass('New technician password: ')
        if password != getpass('Confirm password: '):raise CommandError('Passwords did not match; no login created.')
        try:user.full_clean(exclude=['password']);validate_password(password,user)
        except ValidationError as exc:raise CommandError('; '.join(exc.messages))
        with transaction.atomic():
            user.set_password(password);user.save();TechnicianAccess.objects.create(user=user,employee=e)
        self.stdout.write(self.style.SUCCESS('Technician login created and employee linked. No administrator permission granted.'))
