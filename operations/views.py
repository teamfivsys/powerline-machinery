from functools import wraps
import hashlib
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from .models import Employee, Assignment, AuditEvent, Enquiry, ServiceJob
from .forms import EmployeeForm, AssignmentForm, EnquiryForm, ServiceJobForm

class ThrottledLoginView(LoginView):
    template_name = "registration/login.html"
    def post(self, request, *args, **kwargs):
        # Proxy must preserve actual REMOTE_ADDR. Do not trust arbitrary forwarded headers.
        ip = request.META.get("REMOTE_ADDR", "unknown")
        username = request.POST.get("username", "").strip().casefold()
        self.keys = ["login-ip:" + hashlib.sha256(ip.encode()).hexdigest(), "login-user:" + hashlib.sha256(username.encode()).hexdigest()]
        if any(cache.get(k, 0) >= 10 for k in self.keys):
            return HttpResponse("Too many login attempts. Wait 15 minutes and try again.", status=429)
        return super().post(request, *args, **kwargs)
    def form_invalid(self, form):
        for key in self.keys:
            cache.add(key, 0, 900)
            try: cache.incr(key)
            except ValueError: cache.set(key, 1, 900)
        return super().form_invalid(form)
    def form_valid(self, form):
        # Retain IP failures until expiry; clear the successful user's counter.
        cache.delete(self.keys[1])
        return super().form_valid(form)

def administrator(view):
    @login_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_superuser: raise PermissionDenied
        return view(request, *args, **kwargs)
    return wrapped

@login_required
def dashboard(request):
    return render(request, "dashboard.html", {"open_enquiries": Enquiry.objects.exclude(status="closed").count() if request.user.is_superuser else None, "active_jobs": ServiceJob.objects.exclude(status="completed").count() if request.user.is_superuser else None, "employee_count": Employee.objects.count(), "assignment_count": Assignment.objects.count(), "recent": Assignment.objects.select_related("employee").defer("employee__salary_amount", "employee__salary_currency", "employee__salary_basis")[:5]})

@login_required
def employees(request):
    # Projection avoids even loading confidential salaries for non-admin users.
    rows = Employee.objects.all() if request.user.is_superuser else Employee.objects.only("id", "name")
    return render(request, "employees.html", {"employees": rows})

@administrator
def employee_form(request, pk=None):
    employee = get_object_or_404(Employee, pk=pk) if pk else None
    form = EmployeeForm(request.POST if request.method == "POST" else None, instance=employee)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            record = form.save()
            AuditEvent.objects.create(actor=request.user, action="employee_updated" if employee else "employee_created", object_type="employee", object_id=record.pk)
        messages.success(request, "Employee record saved.")
        return redirect("employees")
    return render(request, "form.html", {"form": form, "title": "Edit employee" if employee else "Add employee", "eyebrow": "HRMS / Staff records", "cancel_url": "employees", "note": "Salary is visible only to administrators. Currency and pay basis are entered explicitly; no payroll calculation is performed."})

@login_required
def assignments(request):
    return render(request, "assignments.html", {"assignments": Assignment.objects.select_related("employee", "created_by").defer("employee__salary_amount", "employee__salary_currency", "employee__salary_basis")})

@login_required
def assignment_form(request, pk=None):
    item = get_object_or_404(Assignment, pk=pk) if pk else None
    form = AssignmentForm(request.POST if request.method == "POST" else None, instance=item)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            record = form.save(commit=False)
            if not item: record.created_by = request.user
            record.save()
            AuditEvent.objects.create(actor=request.user, action="assignment_updated" if item else "assignment_created", object_type="assignment", object_id=record.pk)
        messages.success(request, "Work allocation saved.")
        return redirect("assignments")
    return render(request, "form.html", {"form": form, "title": "Edit allocation" if item else "Allocate work", "eyebrow": "Operations / Work allocation", "cancel_url": "assignments", "note": "Internal allocation only. Saving does not send an employee notification. Employee accounts and completion flow still need confirmation."})

@login_required
def module_pending(request, module):
    names = {"crm": "CRM", "maintenance": "Maintenance", "field-tracking": "Field Tracking"}
    if module not in names:
        from django.http import Http404
        raise Http404
    return render(request, "pending.html", {"module": names[module], "is_field": module == "field-tracking", "implemented": module in {"crm", "maintenance"}, "destination": "enquiries" if module == "crm" else "service_jobs"})


@administrator
def enquiries(request):
    status = request.GET.get("status", "")
    items = Enquiry.objects.all()
    if status in Enquiry.Status.values: items = items.filter(status=status)
    else: status = ""
    return render(request, "enquiries.html", {"items": items, "statuses": Enquiry.Status.choices, "selected_status": status})

@administrator
def enquiry_form(request, pk=None):
    item = get_object_or_404(Enquiry, pk=pk) if pk else None
    form = EnquiryForm(request.POST if request.method == "POST" else None, instance=item)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            record = form.save(commit=False)
            if not item: record.created_by = request.user
            record.save()
            AuditEvent.objects.create(actor=request.user, action="enquiry_updated" if item else "enquiry_created", object_type="enquiry", object_id=record.pk)
        messages.success(request, "Enquiry saved.")
        return redirect("enquiries")
    return render(request, "form.html", {"form": form, "title": "Edit enquiry" if item else "New enquiry", "eyebrow": "CRM / Customer follow-up", "cancel_url": "enquiries", "note": "Administrator-only. Record a spare-parts or service enquiry, follow-up and actual outcome. No quotes, stock movements, payments or notifications are created."})

@administrator
def service_jobs(request):
    status = request.GET.get("status", "")
    # Explicit technician projection prevents confidential payroll fields being loaded.
    from django.db.models import Prefetch
    items = ServiceJob.objects.select_related("enquiry").prefetch_related(Prefetch("technician", queryset=Employee.objects.only("id", "name")))
    if status in ServiceJob.Status.values: items = items.filter(status=status)
    else: status = ""
    return render(request, "service_jobs.html", {"items": items, "statuses": ServiceJob.Status.choices, "selected_status": status})

@administrator
def service_job_form(request, pk=None):
    item = get_object_or_404(ServiceJob, pk=pk) if pk else None
    form = ServiceJobForm(request.POST if request.method == "POST" else None, instance=item)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            record = form.save(commit=False)
            if not item: record.created_by = request.user
            record.save()
            from .models import LocationShare
            LocationShare.objects.filter(job=record).delete()
            AuditEvent.objects.create(actor=request.user, action="service_job_updated" if item else "service_job_created", object_type="service_job", object_id=record.pk)
        messages.success(request, "Service job saved.")
        return redirect("service_jobs")
    return render(request, "form.html", {"form": form, "title": "Edit service job" if item else "New service job", "eyebrow": "Maintenance / Service work", "cancel_url": "service_jobs", "note": "Administrators manage job details and assign an existing employee. Linked technicians can update only their own service progress. Completing or editing this record stops any current location share. No staff notification is sent."})
