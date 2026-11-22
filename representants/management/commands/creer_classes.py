from django.core.management.base import BaseCommand, CommandError

from representants.models import NIVEAUX, Classe

CODES = {code for code, _ in NIVEAUX}


class Command(BaseCommand):
    help = "Crée les classes de l'année. Le niveau est déduit du 1er caractère : 6A, 2NDE3, 1G2, TG1..."

    def add_arguments(self, parser):
        parser.add_argument("noms", nargs="+")

    def handle(self, noms, **_):
        for nom in noms:
            nom = nom.strip().upper()
            if nom[0] not in CODES:
                raise CommandError(f"{nom} : niveau inconnu (1er caractère parmi {', '.join(sorted(CODES))})")
            _, cree = Classe.objects.get_or_create(nom=nom, defaults={"niveau": nom[0]})
            self.stdout.write(f"{nom} {'créée' if cree else 'existe déjà'}")
