"""Explicit, single-operator release step. Never runs at import or build time.
No URL/secret is printed. Default prints a migration plan only.
"""
import argparse
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.vercel')
import django
from django.core.management import call_command
from django.conf import settings

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--confirm-host',required=True)
    parser.add_argument('--confirm-database',required=True)
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    django.setup()
    db=settings.DATABASES['default']
    if settings.DEBUG or db['ENGINE']!='django.db.backends.postgresql':
        raise SystemExit('Release requires non-debug PostgreSQL settings.')
    if (db['HOST'],db['NAME']) != (args.confirm_host,args.confirm_database):
        raise SystemExit('Target differs from explicitly confirmed host/database; no migration ran.')
    call_command('check',deploy=True,fail_level='ERROR')
    call_command('migrate',plan=True)
    if not args.apply:
        print('Plan only. After backup/review and single-operator approval, add --apply.')
        return
    call_command('migrate',interactive=False)
    call_command('createcachetable')
    call_command('migrate',check=True)
    print('Release database steps completed. This does not publish, enable cron or verify client acceptance.')
if __name__=='__main__':main()
