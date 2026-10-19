from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

class Employee(models.Model):
    name = models.CharField(max_length=120)
    joining_date = models.DateField()
    salary_amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    salary_currency = models.CharField(max_length=3)
    salary_basis = models.CharField(max_length=80, help_text="For example, monthly. Confirm with the client; this is descriptive, not a calculation.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ["name", "pk"]
    def __str__(self): return self.name

class Assignment(models.Model):
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True, max_length=3000)
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="assignments")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ["-created_at", "-pk"]

class AuditEvent(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=80)
    object_type = models.CharField(max_length=40)
    object_id = models.PositiveBigIntegerField()
    occurred_at = models.DateTimeField(auto_now_add=True)
    # No salary, password, work description or email copied into logs.


class Enquiry(models.Model):
    class Kind(models.TextChoices):
        SPARES = "spares", "Spare parts"
        SERVICE = "service", "Service"
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        PROGRESS = "in_progress", "In progress"
        CLOSED = "closed", "Closed"
    customer_name = models.CharField(max_length=160)
    contact = models.CharField(max_length=200, blank=True, help_text="Optional phone or email supplied for this enquiry.")
    kind = models.CharField(max_length=12, choices=Kind.choices)
    summary = models.CharField(max_length=180)
    details = models.TextField(max_length=3000)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OPEN)
    follow_up_notes = models.TextField(max_length=3000, blank=True)
    closure_outcome = models.TextField(max_length=1500, blank=True, help_text="Record the actual outcome before closing; closure does not imply a sale or payment.")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ["-updated_at", "-pk"]
    def clean(self):
        from django.core.exceptions import ValidationError
        if self.status == self.Status.CLOSED and not self.closure_outcome.strip():
            raise ValidationError({"closure_outcome": "Record the enquiry outcome before closing."})
        if self.pk and self.kind != self.Kind.SERVICE and self.service_jobs.exists():
            raise ValidationError({"kind": "This enquiry has linked service jobs. Keep its type as Service."})
    def __str__(self): return f"ENQ-{self.pk}: {self.summary}"


class ServiceJob(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        PROGRESS = "in_progress", "In progress"
        COMPLETED = "completed", "Completed"
    customer_name = models.CharField(max_length=160)
    enquiry = models.ForeignKey(Enquiry, blank=True, null=True, on_delete=models.PROTECT, related_name="service_jobs", help_text="Optional link to an existing Service enquiry; does not close the enquiry automatically.")
    machine = models.CharField(max_length=180, help_text="Machine type and identifying description, e.g. forklift / client asset label. No asset register is implied.")
    fault = models.TextField(max_length=3000)
    technician = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="service_jobs")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OPEN)
    work_done = models.TextField(max_length=3000, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ["-updated_at", "-pk"]
    def clean(self):
        from django.core.exceptions import ValidationError
        if self.status == self.Status.COMPLETED and not self.work_done.strip():
            raise ValidationError({"work_done": "Record the work done before completing this job."})
        if self.enquiry_id and self.enquiry.kind != Enquiry.Kind.SERVICE:
            raise ValidationError({"enquiry": "Only a Service enquiry can be linked to a maintenance job."})
    def __str__(self): return f"JOB-{self.pk}: {self.machine}"


class TechnicianAccess(models.Model):
    # Explicit administrator-managed mapping; never infer employee identity by name.
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="technician_access")
    employee = models.OneToOneField(Employee, on_delete=models.PROTECT, related_name="technician_access")
    def __str__(self): return f"{self.user_id} / employee {self.employee_id}"

class LocationShare(models.Model):
    # Latest sample only. No trail, customer contact, device ID or analytics payload.
    job = models.OneToOneField(ServiceJob, on_delete=models.CASCADE, related_name="location_share")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    token = models.UUIDField(unique=True)
    started_at = models.DateTimeField()
    expires_at = models.DateTimeField()
    captured_at = models.DateTimeField(null=True)
    latitude = models.FloatField(null=True)
    longitude = models.FloatField(null=True)
    accuracy_m = models.FloatField(null=True)


class AccountSecurity(models.Model):
    """Explicitly provisioned/recovered accounts must replace their temporary password."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="account_security")
    must_change_password = models.BooleanField(default=True)
