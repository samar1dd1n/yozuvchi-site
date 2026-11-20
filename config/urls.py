from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from apps.panel.views import panel_page

admin.site.site_header = "Yozuvchi sayti — zaxira admin"
admin.site.site_title = "Zaxira admin"

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("api/", include("config.api_urls")),
    path("panel/", panel_page, name="panel"),
    path("", include("apps.web.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
