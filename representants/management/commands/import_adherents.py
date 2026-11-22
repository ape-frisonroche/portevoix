from django.core.management.base import BaseCommand, CommandError

from representants import services


class Command(BaseCommand):
    help = "Remplace la liste des adhérents par un CSV (ex. export HelloAsso), puis réattribue les places."

    def add_arguments(self, parser):
        parser.add_argument("fichier")
        parser.add_argument("--colonne", help="nom de la colonne email (par défaut : 1re contenant 'mail')")
        parser.add_argument("--delimiteur", default=None, help="détecté automatiquement si absent")

    def handle(self, fichier, colonne, delimiteur, **_):
        with open(fichier, "rb") as f:
            try:
                n, colonne = services.importer_adherents(f.read(), colonne=colonne, delimiteur=delimiteur)
            except ValueError as e:
                raise CommandError(e)
        self.stdout.write(self.style.SUCCESS(f"{n} adhérents importés (colonne « {colonne} »)."))
