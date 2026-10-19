from django.urls import path
from django.contrib.auth import views as auth
from . import views, location_views
from .account_views import SecurePasswordChangeView, SecureLogoutView
urlpatterns = [
 path("", views.dashboard, name="dashboard"),
 path("login/", views.ThrottledLoginView.as_view(), name="login"),
 path("logout/", SecureLogoutView.as_view(), name="logout"),
 path("password/change/", SecurePasswordChangeView.as_view(), name="password_change"),
 path("employees/", views.employees, name="employees"),
 path("employees/new/", views.employee_form, name="employee_new"),
 path("employees/<int:pk>/edit/", views.employee_form, name="employee_edit"),
 path("assignments/", views.assignments, name="assignments"),
 path("assignments/new/", views.assignment_form, name="assignment_new"),
 path("assignments/<int:pk>/edit/", views.assignment_form, name="assignment_edit"),
 path("crm/", views.enquiries, name="enquiries"),
 path("crm/new/", views.enquiry_form, name="enquiry_new"),
 path("crm/<int:pk>/edit/", views.enquiry_form, name="enquiry_edit"),
 path("maintenance/", views.service_jobs, name="service_jobs"),
 path("maintenance/new/", views.service_job_form, name="service_job_new"),
 path("maintenance/<int:pk>/edit/", views.service_job_form, name="service_job_edit"),
 path("my-service/", location_views.my_jobs, name="my_jobs"),
 path("my-service/<int:pk>/", location_views.my_job, name="my_job"),
 path("my-service/<int:pk>/location/start/", location_views.location_start, name="location_start"),
 path("my-service/<int:pk>/location/ping/", location_views.location_ping, name="location_ping"),
 path("my-service/<int:pk>/location/stop/", location_views.location_stop, name="location_stop"),
 path("dispatcher/", location_views.dispatcher, name="dispatcher"),
 path("modules/<slug:module>/", views.module_pending, name="module_pending"),
]
