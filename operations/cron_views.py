"""Bearer-protected cleanup only. Not an installed or guaranteed schedule."""
import secrets
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from .location_views import purge_expired

@require_GET
def purge_locations(request):
    secret = getattr(settings, 'CRON_SECRET', '')
    if len(secret) < 32:
        return JsonResponse({'error': 'Cleanup endpoint not configured.'}, status=503)
    supplied = request.headers.get('Authorization', '')
    if not secrets.compare_digest(supplied.encode(), ('Bearer ' + secret).encode()):
        return JsonResponse({'error': 'Unauthorized.'}, status=401)
    return JsonResponse({'deleted': purge_expired()})
