from django import forms
from django.contrib import admin, messages
from django.db.models import Exists, OuterRef
from django.http import HttpResponse
from django.utils import timezone
from openpyxl import Workbook
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import path

from . import services

from .models import Adherent, Candidature, Classe, Niveau, Parent


class CandidatureInline(admin.TabularInline):
    model = Candidature
    extra = 0
    fields = ["parent", "prenom_enfant", "nom_enfant", "niveau", "classe", "statut", "cree_le"]
    readonly_fields = ["cree_le"]


@admin.register(Parent)
class ParentAdmin(admin.ModelAdmin):
    list_display = ["nom", "prenom", "email", "telephone", "adherent", "partage_coordonnees"]
    search_fields = ["nom", "prenom", "email"]
    inlines = [CandidatureInline]
    change_list_template = "admin/representants/parent/change_list.html"

    def get_urls(self):
        vue = self.admin_site.admin_view(self.relance)
        return [path("relance/", vue, name="representants_parent_relance")] + super().get_urls()

    def relance(self, request):
        """Relance de rentrée, éventuellement pour un seul niveau : confirmation (GET), puis envoi (POST)."""
        if not self.has_change_permission(request):
            return redirect("admin:representants_parent_changelist")
        niveau = Niveau.objects.filter(code=request.POST.get("niveau") or request.GET.get("niveau")).first()
        if request.method == "POST":
            try:
                n = services.relancer_rentree(niveau)
            except Exception as e:  # ex. quota d'envoi dépassé : relancer plus tard renverra aux restants
                messages.error(request, f"Envoi interrompu : {e}")
            else:
                messages.success(request, f"Relance envoyée à {n} parent{'s' if n > 1 else ''}"
                                          f"{f' ({niveau})' if niveau else ''}.")
            return redirect("admin:representants_parent_changelist")
        classes = Classe.objects.filter(niveau=niveau) if niveau else Classe.objects.all()
        return TemplateResponse(request, "admin/representants/parent/relance.html", {
            **self.admin_site.each_context(request), "opts": self.model._meta, "title": "Relance de rentrée",
            "parents": services.parents_a_relancer(niveau).order_by("nom", "prenom"),
            "niveaux": Niveau.objects.all(), "niveau": niveau, "nb_classes": classes.count(),
        })

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
    list_display = ["parent", "prenom_enfant", "nom_enfant", "niveau", "classe", "statut", "cree_le"]
    list_filter = ["statut", "niveau", "classe"]
    search_fields = ["parent__nom", "parent__email", "prenom_enfant", "nom_enfant"]
    list_select_related = ["parent", "classe"]
    change_list_template = "admin/representants/candidature/change_list.html"

    def get_urls(self):
        vue = self.admin_site.admin_view(self.export_excel)
        return [path("export/", vue, name="representants_candidature_export")] + super().get_urls()

    def export_excel(self, request):
        """Exporte en .xlsx les candidatures affichées (mêmes filtres et recherche que la liste)."""
        if not self.has_view_permission(request):
            return redirect("admin:index")
        candidatures = (
            self.get_changelist_instance(request).get_queryset(request)
            .select_related("parent", "classe", "niveau")
            .annotate(adherent=Exists(Adherent.objects.filter(email__iexact=OuterRef("parent__email"))))
            .order_by("niveau__ordre", "classe__nom", "statut", "parent__nom")
        )
        classeur = Workbook()
        feuille = classeur.active
        feuille.title = "Candidatures"
        feuille.append(["Niveau", "Classe", "Statut", "Prénom enfant", "Nom enfant", "Nom", "Prénom", "Email", "Téléphone",
                        "Adhérent", "Partage coordonnées", "Candidature le"])
        for c in candidatures:
            p = c.parent
            feuille.append([str(c.niveau), str(c.classe or ""), c.get_statut_display(), c.prenom_enfant, c.nom_enfant,
                            p.nom, p.prenom, p.email, p.telephone, "oui" if c.adherent else "non",
                            "oui" if p.partage_coordonnees else "non",
                            timezone.localtime(c.cree_le).replace(tzinfo=None)])
        for colonne, largeur in zip("ABCDEFGHIJKL", [10, 8, 22, 15, 18, 18, 15, 30, 15, 9, 10, 18]):
            feuille.column_dimensions[colonne].width = largeur
        feuille.freeze_panes = "A2"
        feuille.auto_filter.ref = feuille.dimensions
        reponse = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        reponse["Content-Disposition"] = f'attachment; filename="candidatures-{timezone.localdate()}.xlsx"'
        classeur.save(reponse)
        return reponse


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
