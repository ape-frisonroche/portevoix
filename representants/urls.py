from django.urls import path

from . import views

urlpatterns = [
    path("", views.candidature, name="candidature"),
    path("espace/<str:jeton>/", views.espace, name="espace"),
    path("espace/<str:jeton>/classe/", views.choisir_classe, name="choisir_classe"),
    path("espace/<str:jeton>/supprimer/", views.supprimer, name="supprimer"),
]
