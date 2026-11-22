"""Règles métier : attribution des places, emails, import des adhérents."""

import csv
import io

from django.conf import settings
from django.core import signing
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Exists, OuterRef
from django.template.loader import render_to_string
from django.urls import reverse

from .models import Adherent, Candidature, Classe

SIGNATAIRE = signing.Signer(salt="portevoix.espace")


def lien_espace(parent):
    # Jeton sans horodatage : un seul lien par parent, identique dans tous les emails.
    # ponytail: lien non révocable ; la purge annuelle supprime le parent (les pk SQLite ne sont pas réutilisés)
    return settings.SITE_URL + reverse("espace", args=[SIGNATAIRE.sign(str(parent.pk))])


def parent_id_depuis_jeton(jeton):
    return int(SIGNATAIRE.unsign(jeton))


def envoyer(parent, sujet, gabarit, **contexte):
    contexte.update(parent=parent, lien=lien_espace(parent), kit_url=settings.KIT_URL)
    corps = render_to_string(f"representants/emails/{gabarit}.txt", contexte)
    send_mail(f"[Porte-Voix] {sujet}", corps, None, [parent.email])


@transaction.atomic
def attribuer(classe):
    """Attribue les places libres d'une classe.

    Un parent délégué retenu n'est jamais remplacé. Les places libres vont aux
    adhérents d'abord, puis par date de candidature ; les autres vont en attente.
    """
    actives = classe.candidatures.select_for_update().exclude(statut=Candidature.RETIRE)
    places = settings.MAX_REPRESENTANTS - actives.filter(statut=Candidature.RETENU).count()
    file = (
        actives.exclude(statut=Candidature.RETENU)
        .annotate(adherent=Exists(Adherent.objects.filter(email__iexact=OuterRef("parent__email"))))
        .order_by("-adherent", "cree_le")
        .select_related("parent")
    )
    for c in file:
        nouveau = Candidature.RETENU if places > 0 else Candidature.ATTENTE
        places -= nouveau == Candidature.RETENU
        if c.statut != nouveau:
            c.statut = nouveau
            c.save(update_fields=["statut"])
            transaction.on_commit(lambda c=c: notifier(c))


def notifier(candidature):
    classe = candidature.classe
    if candidature.statut == Candidature.RETENU:
        collegues = [
            c.parent for c in classe.candidatures.filter(statut=Candidature.RETENU, parent__partage_coordonnees=True)
            .exclude(pk=candidature.pk).select_related("parent")
        ]
        envoyer(candidature.parent, f"Vous êtes parent délégué de la {classe}", "retenu",
                classe=classe, collegues=collegues)
    elif candidature.statut == Candidature.ATTENTE:
        envoyer(candidature.parent, f"Liste d'attente pour la {classe}", "attente", classe=classe)


def importer_adherents(contenu, remplacer=True, colonne=None, delimiteur=None):
    """Importe les emails d'un CSV (ex. export HelloAsso) et réattribue les places.

    `contenu` : octets du fichier (UTF-8 ou encodage Excel Windows). La colonne email est la
    première dont le nom contient « mail », sauf si `colonne` est donnée.
    Renvoie (nombre d'emails du fichier, colonne utilisée) ; ValueError si pas de colonne email.
    """
    try:
        texte = contenu.decode("utf-8-sig")
    except UnicodeDecodeError:
        texte = contenu.decode("cp1252")
    if not delimiteur:
        try:
            delimiteur = csv.Sniffer().sniff(texte[:4096], delimiters=",;\t").delimiter
        except csv.Error:  # une seule colonne
            delimiteur = ","
    lecteur = csv.DictReader(io.StringIO(texte), delimiter=delimiteur)
    champs = lecteur.fieldnames or []
    colonne = colonne or next((c for c in champs if "mail" in c.lower()), None)
    if colonne not in champs:
        raise ValueError(f"Colonne email introuvable dans : {', '.join(champs) or '(fichier vide)'}")
    emails = {l[colonne].strip().lower() for l in lecteur if "@" in (l[colonne] or "")}

    with transaction.atomic():
        if remplacer:
            Adherent.objects.all().delete()
        Adherent.objects.bulk_create((Adherent(email=e) for e in emails), ignore_conflicts=True)
        for classe in Classe.objects.all():
            attribuer(classe)
    return len(emails), colonne
