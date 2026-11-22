from datetime import timedelta
from io import StringIO

from django.core import mail
from django.core.management import CommandError, call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from . import services
from .models import Adherent, Candidature, Classe, Niveau, Parent


def candidat(n, classe, adherent=False):
    p = Parent.objects.create(email=f"p{n}@x.fr", prenom=f"P{n}", nom="N", consentement_le=timezone.now())
    if adherent:
        Adherent.objects.create(email=p.email)
    c = Candidature.objects.create(parent=p, prenom_enfant="E", niveau_id="4", classe=classe)
    # dates de candidature croissantes
    Candidature.objects.filter(pk=c.pk).update(cree_le=timezone.now() + timedelta(minutes=n))
    return c


def statuts(*cands):
    return [Candidature.objects.get(pk=c.pk).statut for c in cands]


class AttributionTest(TestCase):
    def setUp(self):
        self.classe = Classe.objects.create(nom="4D", niveau_id="4")

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
        self.assertIn("parent délégué de la 4D", mail.outbox[-1].subject)


class NiveauTest(TestCase):
    def test_niveau_deduit_du_plus_long_code(self):
        Niveau.objects.create(code="2PRO", libelle="2de pro")
        call_command("creer_classes", "2pro1", "2A", stdout=StringIO())
        self.assertEqual(Classe.objects.get(nom="2PRO1").niveau_id, "2PRO")
        self.assertEqual(Classe.objects.get(nom="2A").niveau_id, "2")
        with self.assertRaises(CommandError):
            call_command("creer_classes", "XYZ", stdout=StringIO())


class ParcoursTest(TestCase):
    def test_candidature_puis_classe(self):
        r = self.client.post(reverse("candidature"), {
            "prenom": "Ana", "nom": "B", "email": "Ana@X.fr", "prenom_enfant": "Léo", "nom_enfant": "Martin",
            "niveau": "4", "consentement": "on",
        })
        self.assertEqual(r.status_code, 200)
        parent = Parent.objects.get(email="ana@x.fr")
        lien = services.lien_espace(parent).split("/espace/")[1].rstrip("/")
        classe = Classe.objects.create(nom="4D", niveau_id="4")
        cand = parent.candidatures.get()
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse("choisir_classe", args=[lien]), {"candidature": cand.pk, "classe": classe.pk})
        cand.refresh_from_db()
        self.assertEqual((cand.classe, cand.statut), (classe, "retenu"))
        self.assertIn("parent délégué de la 4D", mail.outbox[-1].subject)

    def test_un_lien_par_parent_pour_tous_ses_enfants(self):
        parent = Parent.objects.create(email="a@x.fr", prenom="A", nom="B", consentement_le=timezone.now())
        lien = services.lien_espace(parent)
        self.assertEqual(lien, services.lien_espace(parent))  # stable d'un email à l'autre
        jeton = lien.split("/espace/")[1].rstrip("/")
        for prenom, nom in (("Léo", "Martin"), ("Zoé", "Martin"), ("léo", "MARTIN"), ("Léo", "Durand")):
            self.client.post(reverse("ajouter_enfant", args=[jeton]),
                             {"prenom_enfant": prenom, "nom_enfant": nom, "niveau": "4"})
        # doublon ignoré (même prénom et nom), homonyme de prénom accepté
        self.assertEqual(sorted(c.enfant for c in parent.candidatures.all()), ["Léo Durand", "Léo Martin", "Zoé Martin"])

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


class AdminCodeEmailTest(TestCase):
    def test_mot_de_passe_puis_code_par_email(self):
        import re
        from django.contrib.auth.models import User
        User.objects.create_superuser("chef", "chef@ape.fr", "mdp-tres-long-123")
        r = self.client.post(reverse("admin:login") + "?next=/admin/",
                             {"username": "chef", "password": "mdp-tres-long-123"}, follow=True)
        self.assertContains(r, "envoyé à chef@ape.fr")
        self.assertEqual(self.client.get("/admin/").status_code, 302)  # pas encore vérifié
        code = re.search(r"\d{6}", mail.outbox[-1].subject).group()
        mauvais = self.client.post(reverse("admin:code"), {"code": "000000" if code != "000000" else "111111"})
        self.assertContains(mauvais, "Code invalide")
        from django_otp.plugins.otp_email.models import EmailDevice
        EmailDevice.objects.update(throttling_failure_count=0)  # lève le délai anti-force brute
        self.client.post(reverse("admin:code") + "?next=/admin/", {"code": code})
        self.assertEqual(self.client.get("/admin/").status_code, 200)


class ImportAdherentsTest(TestCase):
    def test_import_csv(self):
        n, col = services.importer_adherents("Nom;E-mail\nAndré;A@x.fr\nB;b@x.fr\n".encode("cp1252"))
        self.assertEqual((n, col), (2, "E-mail"))
        services.importer_adherents(b"email\nc@x.fr\n", remplacer=False)  # ajout, une seule colonne
        self.assertEqual(sorted(Adherent.objects.values_list("email", flat=True)), ["a@x.fr", "b@x.fr", "c@x.fr"])
        services.importer_adherents(b"email\nc@x.fr\n", remplacer=True)
        self.assertEqual(Adherent.objects.count(), 1)
        with self.assertRaises(ValueError):
            services.importer_adherents(b"nom\nX\n")

    def test_import_depuis_l_admin(self):
        from django.contrib.auth.models import User
        from django.core.files.uploadedfile import SimpleUploadedFile
        from django_otp import DEVICE_ID_SESSION_KEY
        from django_otp.plugins.otp_email.models import EmailDevice
        user = User.objects.create_superuser("chef", "chef@ape.fr", "x")
        self.client.force_login(user)
        session = self.client.session
        session[DEVICE_ID_SESSION_KEY] = EmailDevice.objects.create(user=user, name="email").persistent_id
        session.save()
        self.assertContains(self.client.get(reverse("admin:representants_adherent_changelist")), "Importer un CSV")
        r = self.client.post(reverse("admin:representants_adherent_importer"),
                             {"fichier": SimpleUploadedFile("a.csv", b"Email\nz@x.fr\n")}, follow=True)
        self.assertContains(r, "1 adhérents importés")
        self.assertTrue(Adherent.objects.filter(email="z@x.fr").exists())


class RelanceAdminTest(TestCase):
    def test_relance_depuis_l_admin(self):
        from django.contrib.auth.models import User
        from django_otp import DEVICE_ID_SESSION_KEY
        from django_otp.plugins.otp_email.models import EmailDevice
        user = User.objects.create_superuser("chef", "chef@ape.fr", "x")
        self.client.force_login(user)
        session = self.client.session
        session[DEVICE_ID_SESSION_KEY] = EmailDevice.objects.create(user=user, name="email").persistent_id
        session.save()
        classe = Classe.objects.create(nom="4D", niveau_id="4")
        a_relancer = candidat(1, None).parent
        candidat(2, classe)  # a déjà une classe : pas relancé
        url = reverse("admin:representants_parent_relance")
        self.assertContains(self.client.get(url), a_relancer.email)
        self.assertEqual(len(mail.outbox), 0)  # la page de confirmation n'envoie rien
        r = self.client.post(url, follow=True)
        self.assertContains(r, "Relance envoyée à 1 parent.")
        self.assertEqual([m.to for m in mail.outbox], [[a_relancer.email]])

    def test_relance_par_niveau(self):
        en_6e = candidat(1, None)
        Candidature.objects.filter(pk=en_6e.pk).update(niveau_id="6")
        candidat(2, None)  # 4e
        self.assertEqual(list(services.parents_a_relancer("6")), [en_6e.parent])
        self.assertEqual(services.parents_a_relancer().count(), 2)
        self.assertEqual(services.relancer_rentree("6"), 1)


class ExportExcelTest(TestCase):
    def test_export_filtre(self):
        from io import BytesIO
        from django.contrib.auth.models import User
        from django_otp import DEVICE_ID_SESSION_KEY
        from django_otp.plugins.otp_email.models import EmailDevice
        from openpyxl import load_workbook
        user = User.objects.create_superuser("chef", "chef@ape.fr", "x")
        self.client.force_login(user)
        session = self.client.session
        session[DEVICE_ID_SESSION_KEY] = EmailDevice.objects.create(user=user, name="email").persistent_id
        session.save()
        classe = Classe.objects.create(nom="4D", niveau_id="4")
        candidat(1, classe, adherent=True)
        candidat(2, None)
        url = reverse("admin:representants_candidature_export")
        lignes = lambda r: list(load_workbook(BytesIO(r.content)).active.iter_rows(values_only=True))
        self.assertEqual(len(lignes(self.client.get(url))), 3)  # en-tête + 2
        filtre = lignes(self.client.get(url + f"?classe__id__exact={classe.pk}"))
        self.assertEqual(len(filtre), 2)
        self.assertEqual(filtre[1][:3], ("4e", "4D", "Candidat (classe inconnue)"))
        self.assertEqual(filtre[1][9], "oui")  # adhérent
