from django.contrib.auth.views import PasswordChangeView, LogoutView
from django.contrib.auth.forms import PasswordChangeForm
from django.core.exceptions import ValidationError
from django.db import transaction
from .models import AccountSecurity, AuditEvent, LocationShare

class DifferentPasswordForm(PasswordChangeForm):
    def clean(self):
        cleaned = super().clean()
        password = cleaned.get("new_password2")
        if password and self.user.check_password(password):
            self.add_error("new_password2", ValidationError("Choose a different password, not your current or temporary password."))
        return cleaned

class SecurePasswordChangeView(PasswordChangeView):
    form_class = DifferentPasswordForm
    template_name = "registration/password_change.html"
    success_url = "/"
    def form_valid(self, form):
        with transaction.atomic():
            response = super().form_valid(form)
            AccountSecurity.objects.filter(user=self.request.user).update(must_change_password=False)
            LocationShare.objects.filter(user=self.request.user).delete()
            AuditEvent.objects.create(actor=self.request.user, action="password_changed", object_type="account", object_id=self.request.user.pk)
        return response

class SecureLogoutView(LogoutView):
    def post(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            LocationShare.objects.filter(user=request.user).delete()
        return super().post(request, *args, **kwargs)
