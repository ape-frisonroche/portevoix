from django import forms

from .models import NIVEAUX


class EnfantForm(forms.Form):
    prenom_enfant = forms.CharField(label="Prénom de l'enfant", max_length=100)
    niveau = forms.ChoiceField(label="Niveau à la rentrée", choices=NIVEAUX)


class CandidatureForm(EnfantForm):
    field_order = ["prenom", "nom", "email", "telephone", "prenom_enfant", "niveau"]
    prenom = forms.CharField(label="Votre prénom", max_length=100)
    nom = forms.CharField(label="Votre nom", max_length=100)
    email = forms.EmailField(label="Votre email")
    telephone = forms.CharField(label="Téléphone (facultatif)", max_length=20, required=False)
    consentement = forms.BooleanField(
        label="J'accepte que l'APE traite ces données pour la désignation des représentants des parents.",
    )
    partage_coordonnees = forms.BooleanField(
        required=False,
        label="J'accepte que mes coordonnées soient transmises aux autres représentants "
              "de la classe et au chef d'établissement.",
    )

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()
