from django.urls import path, include
from operations.cron_views import purge_locations
urlpatterns = [path("internal/cron/purge-locations/", purge_locations, name="cron_purge_locations"), path("", include("operations.urls"))]
