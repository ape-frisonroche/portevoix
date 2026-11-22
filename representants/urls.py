from django.urls import path

from . import views

urlpatterns = [
    path("", views.accueil, name="accueil"),
    path("candidater/", views.candidature, name="candidature"),
    path("lien-perdu/", views.lien_perdu, name="lien_perdu"),
    path("espace/<str:jeton>/", views.espace, name="espace"),
    path("espace/<str:jeton>/classe/", views.choisir_classe, name="choisir_classe"),
    path("espace/<str:jeton>/enfant/", views.ajouter_enfant, name="ajouter_enfant"),
    path("espace/<str:jeton>/retirer/", views.retirer, name="retirer"),
    path("espace/<str:jeton>/supprimer/", views.supprimer, name="supprimer"),
]
