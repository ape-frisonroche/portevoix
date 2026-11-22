from datetime import timedelta

from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from . import services
from .models import Adherent, Candidature, Classe, Parent


def candidat(n, classe, adherent=False):
    p = Parent.objects.create(email=f"p{n}@x.fr", prenom=f"P{n}", nom="N", consentement_le=timezone.now())
    if adherent:
        Adherent.objects.create(email=p.email)
    c = Candidature.objects.create(parent=p, prenom_enfant="E", niveau="4", classe=classe)
    # dates de candidature croissantes
    Candidature.objects.filter(pk=c.pk).update(cree_le=timezone.now() + timedelta(minutes=n))
    return c


def statuts(*cands):
    return [Candidature.objects.get(pk=c.pk).statut for c in cands]


class AttributionTest(TestCase):
    def setUp(self):
        self.classe = Classe.objects.create(nom="4D", niveau="4")

    def test_quatre_places_adherents_prioritaires(self):
        c = [candidat(i, self.classe) for i in range(4)] + [candidat(4, self.classe, adherent=True)]
        services.attribuer(self.classe)
        # l'adhérent passe devant ; le dernier non-adhérent par date est en attente
        self.assertEqual(statuts(*c), ["retenu", "retenu", "retenu", "attente", "retenu"])

    def test_un_retenu_n_est_jamais_remplace(self):
        c = [candidat(i, self.classe) for i in range(4)]
        services.attribuer(self.classe)
        tard = candidat(9, self.classe, adherent=True)
        services.attribuer(self.classe)
        self.assertEqual(statuts(*c, tard), ["retenu"] * 4 + ["attente"])

    def test_retrait_promeut_la_liste_d_attente(self):
        c = [candidat(i, self.classe) for i in range(5)]
        services.attribuer(self.classe)
        c[0].parent.delete()
        services.attribuer(self.classe)
        self.assertEqual(statuts(*c[1:]), ["retenu"] * 4)


    def test_retrait_d_un_enfant_par_le_parent(self):
        c = [candidat(i, self.classe) for i in range(5)]
        services.attribuer(self.classe)
        jeton = services.lien_espace(c[0].parent).split("/espace/")[1].rstrip("/")
        # un parent ne peut pas retirer la candidature d'un autre
        r = self.client.post(reverse("retirer", args=[jeton]), {"candidature": c[1].pk})
        self.assertEqual(r.status_code, 404)
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse("retirer", args=[jeton]), {"candidature": c[0].pk})
        self.assertFalse(Candidature.objects.filter(pk=c[0].pk).exists())
        self.assertEqual(statuts(*c[1:]), ["retenu"] * 4)
        self.assertIn("représentant de la 4D", mail.outbox[-1].subject)


class ParcoursTest(TestCase):
    def test_candidature_puis_classe(self):
        r = self.client.post(reverse("candidature"), {
            "prenom": "Ana", "nom": "B", "email": "Ana@X.fr", "prenom_enfant": "Léo",
            "niveau": "4", "consentement": "on",
        })
        self.assertEqual(r.status_code, 200)
        parent = Parent.objects.get(email="ana@x.fr")
        lien = services.lien_espace(parent).split("/espace/")[1].rstrip("/")
        classe = Classe.objects.create(nom="4D", niveau="4")
        cand = parent.candidatures.get()
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse("choisir_classe", args=[lien]), {"candidature": cand.pk, "classe": classe.pk})
        cand.refresh_from_db()
        self.assertEqual((cand.classe, cand.statut), (classe, "retenu"))
        self.assertIn("représentant de la 4D", mail.outbox[-1].subject)

    def test_un_lien_par_parent_pour_tous_ses_enfants(self):
        parent = Parent.objects.create(email="a@x.fr", prenom="A", nom="B", consentement_le=timezone.now())
        lien = services.lien_espace(parent)
        self.assertEqual(lien, services.lien_espace(parent))  # stable d'un email à l'autre
        jeton = lien.split("/espace/")[1].rstrip("/")
        for prenom in ("Léo", "Zoé", "léo"):  # doublon ignoré
            self.client.post(reverse("ajouter_enfant", args=[jeton]), {"prenom_enfant": prenom, "niveau": "4"})
        self.assertEqual(sorted(parent.candidatures.values_list("prenom_enfant", flat=True)), ["Léo", "Zoé"])

    def test_lien_perdu(self):
        parent = Parent.objects.create(email="a@x.fr", prenom="A", nom="B", consentement_le=timezone.now())
        connu = self.client.post(reverse("lien_perdu"), {"email": " A@X.fr "})
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(services.lien_espace(parent), mail.outbox[0].body)
        inconnu = self.client.post(reverse("lien_perdu"), {"email": "z@x.fr"})
        self.assertEqual(len(mail.outbox), 1)  # rien envoyé, même page affichée
        self.assertEqual(connu.content.replace(b"A@X.fr", b""), inconnu.content.replace(b"z@x.fr", b""))

    def test_accueil_mene_au_formulaire(self):
        r = self.client.get(reverse("accueil"))
        self.assertContains(r, reverse("candidature"))
        self.assertContains(r, reverse("lien_perdu"))

    def test_groupe_bureau(self):
        from django.contrib.auth.models import Group
        perms = set(Group.objects.get(name="Bureau").permissions.values_list("codename", flat=True))
        self.assertIn("change_candidature", perms)
        self.assertNotIn("add_user", perms)  # pas de gestion des comptes

    def test_lien_falsifie(self):
        r = self.client.get(reverse("espace", args=["faux"]))
        self.assertEqual(r.status_code, 400)
