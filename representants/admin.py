from django import forms
from django.contrib import admin, messages
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import path

from . import services

from .models import Adherent, Candidature, Classe, Niveau, Parent


class CandidatureInline(admin.TabularInline):
    model = Candidature
    extra = 0
    fields = ["parent", "prenom_enfant", "niveau", "classe", "statut", "cree_le"]
    readonly_fields = ["cree_le"]


@admin.register(Parent)
class ParentAdmin(admin.ModelAdmin):
    list_display = ["nom", "prenom", "email", "telephone", "adherent", "partage_coordonnees"]
    search_fields = ["nom", "prenom", "email"]
    inlines = [CandidatureInline]

    @admin.display(boolean=True)
    def adherent(self, obj):
        return obj.adherent


@admin.register(Classe)
class ClasseAdmin(admin.ModelAdmin):
    list_display = ["nom", "niveau", "nb_retenus", "nb_attente"]
    list_filter = ["niveau"]
    inlines = [CandidatureInline]

    @admin.display(description="retenus")
    def nb_retenus(self, obj):
        return obj.candidatures.filter(statut=Candidature.RETENU).count()

    @admin.display(description="en attente")
    def nb_attente(self, obj):
        return obj.candidatures.filter(statut=Candidature.ATTENTE).count()


@admin.register(Candidature)
class CandidatureAdmin(admin.ModelAdmin):
    list_display = ["parent", "prenom_enfant", "niveau", "classe", "statut", "cree_le"]
    list_filter = ["statut", "niveau", "classe"]
    search_fields = ["parent__nom", "parent__email", "prenom_enfant"]
    list_select_related = ["parent", "classe"]


class ImportAdherentsForm(forms.Form):
    fichier = forms.FileField(label="Fichier CSV", help_text="Ex. export HelloAsso. La colonne dont le nom contient « mail » est utilisée.")
    remplacer = forms.BooleanField(
        label="Remplacer toute la liste (sinon les emails sont ajoutés aux adhérents existants)", required=False,
    )


@admin.register(Adherent)
class AdherentAdmin(admin.ModelAdmin):
    search_fields = ["email"]
    change_list_template = "admin/representants/adherent/change_list.html"

    def get_urls(self):
        vue = self.admin_site.admin_view(self.importer)
        return [path("importer/", vue, name="representants_adherent_importer")] + super().get_urls()

    def importer(self, request):
        if not self.has_add_permission(request):
            return redirect("admin:representants_adherent_changelist")
        form = ImportAdherentsForm(request.POST or None, request.FILES or None)
        if form.is_valid():
            try:
                n, colonne = services.importer_adherents(
                    form.cleaned_data["fichier"].read(), remplacer=form.cleaned_data["remplacer"])
            except ValueError as e:
                form.add_error("fichier", str(e))
            else:
                messages.success(request, f"{n} adhérents importés (colonne « {colonne} »). Places réattribuées.")
                return redirect("admin:representants_adherent_changelist")
        return TemplateResponse(request, "admin/representants/adherent/importer.html", {
            **self.admin_site.each_context(request), "form": form, "opts": self.model._meta,
            "title": "Importer des adhérents (CSV)",
        })


@admin.register(Niveau)
class NiveauAdmin(admin.ModelAdmin):
    list_display = ["code", "libelle", "ordre"]
    list_editable = ["libelle", "ordre"]

    def get_readonly_fields(self, request, obj=None):
        return ["code"] if obj else []  # le code sert de clé : le changer casserait les liens
