"""Admin en deux étapes : mot de passe, puis code à 6 chiffres reçu par email."""

from django.contrib import admin
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django_otp import login as otp_login
from django_otp.plugins.otp_email.models import EmailDevice


class AdminSite(admin.AdminSite):
    site_header = "Porte-Voix — administration"

    def has_permission(self, request):
        return super().has_permission(request) and request.user.is_verified()

    def login(self, request, extra_context=None):
        # mot de passe déjà validé : passer à l'étape du code
        if request.user.is_authenticated and request.user.is_staff and not request.user.is_verified():
            return redirect(f"{reverse('admin:code')}?{request.GET.urlencode()}")
        return super().login(request, extra_context)

    def get_urls(self):
        return [path("code/", self.code, name="code")] + super().get_urls()

    def code(self, request):
        user = request.user
        if not (user.is_authenticated and user.is_staff):
            return redirect("admin:login")
        suivant = request.GET.get("next", "")
        if not url_has_allowed_host_and_scheme(suivant, {request.get_host()}):
            suivant = reverse("admin:index")
        device, _ = EmailDevice.objects.get_or_create(user=user, defaults={"name": "email"})
        erreur = info = None
        if not user.email:
            erreur = "Votre compte n'a pas d'adresse email : demandez à un super-utilisateur de l'ajouter."
        elif request.method == "POST":
            if device.verify_token(request.POST.get("code", "").strip()):
                otp_login(request, device)
                return redirect(suivant)
            erreur = "Code invalide ou expiré."
        else:
            # renvoyé à chaque affichage, au plus une fois par minute (délai géré par django-otp)
            device.generate_challenge()
            info = f"Un code vient d'être envoyé à {user.email}. Il est valable 5 minutes."
        return TemplateResponse(request, "admin/code.html", {
            **self.each_context(request), "title": "Code de connexion",
            "erreur": erreur, "info": info, "a_email": bool(user.email),
        })
