from django.contrib import admin
from django.urls import include, path
from django_otp.admin import OTPAdminSite

# Admin protégé par double authentification (TOTP)
admin.site.__class__ = OTPAdminSite
admin.site.site_header = "Porte-Voix — administration"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("representants.urls")),
]
