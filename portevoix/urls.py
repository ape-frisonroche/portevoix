from django.contrib import admin
from django.urls import include, path

from .admin_site import AdminSite

# Admin protégé par mot de passe + code reçu par email
admin.site.__class__ = AdminSite

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("representants.urls")),
]
