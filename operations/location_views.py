"""Explicit foreground-only, per-assigned-job location sharing.
No geolocation lookup occurs on the server. Samples come only from the opt-in browser UI.
"""
from datetime import timedelta
from functools import wraps
import math
import uuid
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_POST
from .forms import TechnicianJobForm
from .models import ServiceJob, TechnicianAccess, LocationShare, AuditEvent
from .views import administrator

TTL_SECONDS = 120

def purge_expired():
    return LocationShare.objects.filter(expires_at__lte=timezone.now()).delete()[0]

def technician(view):
    @login_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        try: request.technician_employee_id = TechnicianAccess.objects.only("employee_id").get(user=request.user).employee_id
        except TechnicianAccess.DoesNotExist: raise PermissionDenied
        return view(request, *args, **kwargs)
    return wrapped

def assigned_job(request, pk):
    return get_object_or_404(ServiceJob, pk=pk, technician_id=request.technician_employee_id)

@technician
def my_jobs(request):
    return render(request, "my_jobs.html", {"items": ServiceJob.objects.filter(technician_id=request.technician_employee_id)})

@technician
def my_job(request, pk):
    item = assigned_job(request, pk)
    form = TechnicianJobForm(request.POST if request.method == "POST" else None, instance=item)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            # Do not save excluded instance fields; this also prevents stale POSTs
            # from restoring an assignment changed by an administrator.
            updated = ServiceJob.objects.filter(pk=item.pk, technician_id=request.technician_employee_id).update(status=form.cleaned_data["status"], work_done=form.cleaned_data["work_done"], updated_at=timezone.now())
            if not updated: raise PermissionDenied
            if form.cleaned_data["status"] == "completed": LocationShare.objects.filter(job_id=item.pk).delete()
            AuditEvent.objects.create(actor=request.user, action="service_progress_updated", object_type="service_job", object_id=item.pk)
        messages.success(request, "Service progress saved.")
        return redirect("my_job", pk=item.pk)
    return render(request, "my_job.html", {"item": item, "form": form})

@technician
@require_POST
def location_start(request, pk):
    item = assigned_job(request, pk)
    if item.status == "completed": return JsonResponse({"error":"Completed jobs cannot share location."},status=409)
    if request.POST.get("consent") != "foreground": return JsonResponse({"error":"Explicit foreground-sharing consent is required."}, status=400)
    now = timezone.now()
    with transaction.atomic():
        purge_expired()
        LocationShare.objects.filter(user=request.user).delete()
        share,_ = LocationShare.objects.update_or_create(job=item, defaults={"user":request.user,"token":uuid.uuid4(),"started_at":now,"expires_at":now+timedelta(seconds=TTL_SECONDS),"latitude":None,"longitude":None,"accuracy_m":None,"captured_at":None})
    return JsonResponse({"token":str(share.token),"expires_in":TTL_SECONDS})

@technician
@require_POST
def location_ping(request, pk):
    item = assigned_job(request, pk)
    purge_expired()
    if item.status == "completed":
        LocationShare.objects.filter(job=item).delete()
        return JsonResponse({"error":"This job is completed."},status=409)
    try:
        token=uuid.UUID(request.POST.get("token",""))
        lat=float(request.POST["latitude"]);lon=float(request.POST["longitude"]);accuracy=float(request.POST["accuracy_m"])
        captured=parse_datetime(request.POST["captured_at"])
        if not (math.isfinite(lat) and math.isfinite(lon) and math.isfinite(accuracy)) or not (-90<=lat<=90 and -180<=lon<=180 and 0<=accuracy<=100000): raise ValueError
        if captured is None or timezone.is_naive(captured): raise ValueError
        now=timezone.now();age=(now-captured).total_seconds()
        if age < -30 or age > TTL_SECONDS: raise ValueError
    except (KeyError,ValueError,TypeError,OverflowError):
        return JsonResponse({"error":"Invalid or outdated location sample."},status=400)
    share=LocationShare.objects.filter(job=item,user=request.user,token=token).first()
    if share is None: return JsonResponse({"error":"Sharing stopped or expired. Start again to share."},status=409)
    if share.captured_at and captured < share.captured_at: return JsonResponse({"error":"Out-of-order sample rejected."},status=400)
    # Conditional update prevents a stopped/reassigned session being recreated by a late ping.
    changed=LocationShare.objects.filter(pk=share.pk,token=token,user=request.user,expires_at__gt=now,job__technician_id=request.technician_employee_id).exclude(job__status="completed").filter(Q(captured_at__isnull=True) | Q(captured_at__lte=captured)).update(latitude=round(lat,6),longitude=round(lon,6),accuracy_m=round(accuracy,1),captured_at=captured,expires_at=min(now,captured)+timedelta(seconds=TTL_SECONDS))
    if not changed: return JsonResponse({"error":"Sharing session ended."},status=409)
    return JsonResponse({"saved":True,"expires_in":TTL_SECONDS})

@technician
@require_POST
def location_stop(request, pk):
    item=assigned_job(request, pk)
    try:token=uuid.UUID(request.POST.get("token",""))
    except (ValueError,TypeError):return JsonResponse({"error":"Invalid session."},status=400)
    LocationShare.objects.filter(job=item,user=request.user,token=token).delete()
    return JsonResponse({"stopped":True})

@administrator
def dispatcher(request):
    purge_expired()
    rows=[];now=timezone.now()
    for share in LocationShare.objects.select_related("job","user"):
        # Reassignment or access removal revokes viewing immediately.
        access=TechnicianAccess.objects.filter(user_id=share.user_id, employee_id=share.job.technician_id, user__is_active=True).exists()
        if not access or share.job.status == "completed":
            share.delete();continue
        age=max(0,int((now-share.captured_at).total_seconds())) if share.captured_at else None
        rows.append({"share":share,"age":age,"stale":age is not None and age>30})
    return render(request,"dispatcher.html",{"rows":rows,"server_epoch":now.timestamp()})
