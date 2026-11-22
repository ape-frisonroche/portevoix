from django.conf import settings
from django.contrib import messages
from django.core import signing
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from . import services
from .forms import CandidatureForm, EnfantForm
from .models import Candidature, Classe, Parent


def accueil(request):
    return render(request, "representants/accueil.html", {"places": settings.MAX_REPRESENTANTS})


def candidature(request):
    form = CandidatureForm(request.POST or None)
    if form.is_valid():
        d = form.cleaned_data
        parent, cree = Parent.objects.get_or_create(
            email=d["email"],
            defaults=dict(
                prenom=d["prenom"], nom=d["nom"], telephone=d["telephone"],
                consentement_le=timezone.now(), partage_coordonnees=d["partage_coordonnees"],
            ),
        )
        # Un parent existant n'est pas modifié par ce formulaire public (n'importe qui
        # peut y saisir n'importe quel email) ; il gère ses données via son lien.
        _ajouter_enfant(parent, d)
        services.envoyer(parent, "Confirmez votre candidature", "confirmation")
        return render(request, "representants/merci.html", {"email": parent.email})
    return render(request, "representants/candidature.html",
                  {"form": form, "contact": settings.CONTACT_RGPD})


def lien_perdu(request):
    """Renvoie le lien de l'espace. Même réponse que l'email soit connu ou non."""
    email = request.POST.get("email", "").strip()
    if request.method == "POST" and email:
        # ponytail: pas de limite d'envois, comme le formulaire de candidature ; à ajouter en cas d'abus
        parent = Parent.objects.filter(email__iexact=email).first()
        if parent:
            services.envoyer(parent, "Votre lien personnel", "lien")
        return render(request, "representants/lien_perdu.html", {"email": email, "envoye": True})
    return render(request, "representants/lien_perdu.html")


def _ajouter_enfant(parent, d):
    if not parent.candidatures.filter(prenom_enfant__iexact=d["prenom_enfant"]).exists():
        Candidature.objects.create(parent=parent, prenom_enfant=d["prenom_enfant"], niveau=d["niveau"])


def _parent(jeton):
    try:
        return get_object_or_404(Parent, pk=services.parent_id_depuis_jeton(jeton))
    except signing.BadSignature:  # inclut SignatureExpired
        return None


def espace(request, jeton):
    parent = _parent(jeton)
    if parent is None:
        return render(request, "representants/lien_invalide.html", status=400)
    candidatures = list(parent.candidatures.select_related("classe", "niveau"))
    classes = Classe.objects.all()
    for c in candidatures:
        c.classes_possibles = [k for k in classes if k.niveau_id == c.niveau_id]
    return render(request, "representants/espace.html",
                  {"parent": parent, "candidatures": candidatures, "jeton": jeton, "form": EnfantForm()})


@require_POST
def ajouter_enfant(request, jeton):
    parent = _parent(jeton)
    if parent is None:
        return render(request, "representants/lien_invalide.html", status=400)
    form = EnfantForm(request.POST)
    if form.is_valid():
        _ajouter_enfant(parent, form.cleaned_data)
        messages.success(request, f"Candidature ajoutée pour {form.cleaned_data['prenom_enfant']}.")
    return redirect("espace", jeton=jeton)


@require_POST
def choisir_classe(request, jeton):
    parent = _parent(jeton)
    if parent is None:
        return render(request, "representants/lien_invalide.html", status=400)
    c = get_object_or_404(parent.candidatures, pk=request.POST.get("candidature"),
                          classe__isnull=True)
    classe = get_object_or_404(Classe, pk=request.POST.get("classe"), niveau=c.niveau)
    if parent.candidatures.filter(classe=classe).exists():
        c.delete()
        messages.info(request, f"Vous êtes déjà candidat pour la {classe} : candidature fusionnée.")
    else:
        c.classe = classe
        c.save(update_fields=["classe"])
        services.attribuer(classe)
        messages.success(request, f"Classe {classe} enregistrée.")
    return redirect("espace", jeton=jeton)


@require_POST
def retirer(request, jeton):
    """Retire la candidature d'un enfant et libère sa place."""
    parent = _parent(jeton)
    if parent is None:
        return render(request, "representants/lien_invalide.html", status=400)
    with transaction.atomic():
        c = get_object_or_404(parent.candidatures.select_related("classe"), pk=request.POST.get("candidature"))
        c.delete()
        if c.classe:
            services.attribuer(c.classe)  # promeut la liste d'attente
    messages.success(request, f"Candidature retirée pour {c.prenom_enfant}.")
    return redirect("espace", jeton=jeton)


@require_POST
def supprimer(request, jeton):
    """Droit à l'effacement : supprime le parent et libère ses places."""
    parent = _parent(jeton)
    if parent is None:
        return render(request, "representants/lien_invalide.html", status=400)
    with transaction.atomic():
        classes = list(Classe.objects.filter(candidatures__parent=parent))
        parent.delete()
        for classe in classes:
            services.attribuer(classe)  # promeut la liste d'attente
    return render(request, "representants/supprime.html")
