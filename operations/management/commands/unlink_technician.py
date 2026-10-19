from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand,CommandError
from django.db import transaction
from operations.models import LocationShare,TechnicianAccess
class Command(BaseCommand):
    help='Revoke technician assignment access and clear location sessions, leaving the login itself unchanged.'
    def add_arguments(self,p):p.add_argument('username')
    def handle(self,*args,**opts):
        try:u=get_user_model().objects.get(username=opts['username'])
        except get_user_model().DoesNotExist:raise CommandError('Login not found.')
        with transaction.atomic():LocationShare.objects.filter(user=u).delete();TechnicianAccess.objects.filter(user=u).delete()
        self.stdout.write('Technician access revoked. Existing non-technician login permissions remain unchanged.')
