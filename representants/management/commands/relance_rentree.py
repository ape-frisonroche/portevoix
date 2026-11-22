from django.core.management.base import BaseCommand

from representants import services


class Command(BaseCommand):
    help = "Envoie le lien aux parents dont un enfant n'a pas encore de classe."

    def add_arguments(self, parser):
        parser.add_argument("--niveau", help="code du niveau (ex. 6, 2PRO) ; par défaut tous")

    def handle(self, niveau, **_):
        self.stdout.write(self.style.SUCCESS(f"{services.relancer_rentree(niveau)} parents relancés."))
