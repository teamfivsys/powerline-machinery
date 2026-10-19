import re
from django import forms
from .models import Employee, Assignment
class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = ["name", "joining_date", "salary_amount", "salary_currency", "salary_basis"]
        widgets = {"joining_date": forms.DateInput(attrs={"type": "date"}), "salary_amount": forms.NumberInput(attrs={"step": "0.01", "min": "0"})}
    def clean_salary_currency(self):
        code = self.cleaned_data["salary_currency"].upper().strip()
        if not re.fullmatch(r"[A-Z]{3}", code): raise forms.ValidationError("Enter a three-letter currency code, such as AED or INR; confirm the currency first.")
        return code
class AssignmentForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["employee"].queryset = Employee.objects.only("id", "name")
    class Meta:
        model = Assignment
        fields = ["title", "employee", "description"]
        widgets = {"description": forms.Textarea(attrs={"rows": 4})}


from .models import Enquiry, ServiceJob

class EnquiryForm(forms.ModelForm):
    class Meta:
        model = Enquiry
        fields = ["customer_name", "contact", "kind", "summary", "details", "status", "follow_up_notes", "closure_outcome"]
        widgets = {name: forms.Textarea(attrs={"rows": 3}) for name in ["details", "follow_up_notes", "closure_outcome"]}

class ServiceJobForm(forms.ModelForm):
    class Meta:
        model = ServiceJob
        fields = ["customer_name", "enquiry", "machine", "fault", "technician", "status", "work_done"]
        widgets = {name: forms.Textarea(attrs={"rows": 3}) for name in ["fault", "work_done"]}
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["enquiry"].queryset = Enquiry.objects.filter(kind=Enquiry.Kind.SERVICE)
        # Never load salary fields while building assignee choices.
        self.fields["technician"].queryset = Employee.objects.only("id", "name")


class TechnicianJobForm(forms.ModelForm):
    class Meta:
        model = ServiceJob
        fields = ["status", "work_done"]
        widgets = {"work_done": forms.Textarea(attrs={"rows": 4})}
