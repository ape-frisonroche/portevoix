from django.core.management.base import BaseCommand, CommandError

from representants.models import Classe, Niveau


class Command(BaseCommand):
    help = ("Crée les classes de l'année. Le niveau est le code (admin → Niveaux) qui débute le nom, "
            "le plus long l'emportant : 6A → 6, 2PRO1 → 2PRO, TG1 → T.")

    def add_arguments(self, parser):
        parser.add_argument("noms", nargs="+")

    def handle(self, noms, **_):
        for nom in noms:
            nom = nom.strip().upper()
            niveau = Niveau.depuis_nom_de_classe(nom)
            if niveau is None:
                codes = ", ".join(Niveau.objects.values_list("code", flat=True))
                raise CommandError(f"{nom} : niveau inconnu (le nom doit commencer par un code parmi {codes})")
            _, cree = Classe.objects.get_or_create(nom=nom, defaults={"niveau": niveau})
            self.stdout.write(f"{nom} {'créée' if cree else 'existe déjà'} ({niveau})")
