from django.contrib import admin

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


admin.site.register(Adherent, search_fields=["email"])


@admin.register(Niveau)
class NiveauAdmin(admin.ModelAdmin):
    list_display = ["code", "libelle", "ordre"]
    list_editable = ["libelle", "ordre"]

    def get_readonly_fields(self, request, obj=None):
        return ["code"] if obj else []  # le code sert de clé : le changer casserait les liens
