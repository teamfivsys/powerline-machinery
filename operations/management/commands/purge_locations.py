from django.core.management.base import BaseCommand
from operations.location_views import purge_expired
class Command(BaseCommand):
    help="Delete expired foreground location sessions. Schedule every minute on the selected host."
    def handle(self,*args,**kwargs):self.stdout.write(str(purge_expired())+" expired location sessions deleted.")
