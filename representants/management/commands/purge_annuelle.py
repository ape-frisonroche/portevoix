from django.core.management.base import BaseCommand, CommandError

from representants.models import Adherent, Candidature, Classe, Parent


class Command(BaseCommand):
    help = "Fin d'année scolaire (RGPD) : supprime parents, candidatures, classes et adhérents."

    def add_arguments(self, parser):
        parser.add_argument("--oui", action="store_true", help="confirme la suppression définitive")

    def handle(self, oui, **_):
        if not oui:
            raise CommandError("Suppression définitive : relancez avec --oui (faites une sauvegarde avant).")
        for modele in (Candidature, Parent, Classe, Adherent):
            n, _ = modele.objects.all().delete()
            self.stdout.write(f"{modele.__name__} : {n} supprimés")
