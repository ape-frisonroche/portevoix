import csv

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from representants import services
from representants.models import Adherent, Classe


class Command(BaseCommand):
    help = "Remplace la liste des adhérents par un CSV (ex. export HelloAsso), puis réattribue les places."

    def add_arguments(self, parser):
        parser.add_argument("fichier")
        parser.add_argument("--colonne", help="nom de la colonne email (par défaut : 1re contenant 'mail')")
        parser.add_argument("--delimiteur", default=None, help="détecté automatiquement si absent")

    def handle(self, fichier, colonne, delimiteur, **_):
        with open(fichier, newline="", encoding="utf-8-sig") as f:
            echantillon = f.read(4096)
            f.seek(0)
            delim = delimiteur or csv.Sniffer().sniff(echantillon, delimiters=",;\t").delimiter
            lecteur = csv.DictReader(f, delimiter=delim)
            colonne = colonne or next((c for c in lecteur.fieldnames if "mail" in c.lower()), None)
            if colonne not in (lecteur.fieldnames or []):
                raise CommandError(f"Colonne email introuvable dans : {lecteur.fieldnames}")
            emails = {l[colonne].strip().lower() for l in lecteur if "@" in (l[colonne] or "")}

        with transaction.atomic():
            Adherent.objects.all().delete()
            Adherent.objects.bulk_create(Adherent(email=e) for e in emails)
            for classe in Classe.objects.all():
                services.attribuer(classe)
        self.stdout.write(self.style.SUCCESS(f"{len(emails)} adhérents importés (colonne « {colonne} »)."))
