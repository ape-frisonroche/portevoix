from django import forms

from .models import Niveau


class EnfantForm(forms.Form):
    prenom_enfant = forms.CharField(label="Prénom de l'enfant", max_length=100)
    nom_enfant = forms.CharField(label="Nom de famille de l'enfant", max_length=100)
    niveau = forms.ModelChoiceField(label="Niveau à la rentrée", queryset=Niveau.objects.all(), empty_label=None)


class CandidatureForm(EnfantForm):
    field_order = ["prenom", "nom", "email", "telephone", "prenom_enfant", "nom_enfant", "niveau"]
    prenom = forms.CharField(label="Votre prénom", max_length=100)
    nom = forms.CharField(label="Votre nom", max_length=100)
    email = forms.EmailField(label="Votre email")
    telephone = forms.CharField(label="Téléphone (facultatif)", max_length=20, required=False)
    consentement = forms.BooleanField(
        label="J'accepte que l'APE traite ces données pour la désignation des parents délégués.",
    )
    partage_coordonnees = forms.BooleanField(
        required=False,
        label="J'accepte que mes coordonnées soient transmises aux autres parents délégués "
              "de la classe et au chef d'établissement.",
    )

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()
