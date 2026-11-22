from django.core.management.base import BaseCommand

from representants import services
from representants.models import Parent


class Command(BaseCommand):
    help = "Envoie le lien aux parents dont un enfant n'a pas encore de classe."

    def handle(self, **_):
        parents = Parent.objects.filter(candidatures__classe__isnull=True, candidatures__statut="candidat").distinct()
        for p in parents:
            services.envoyer(p, "Indiquez la classe de votre enfant", "rentree")
        self.stdout.write(self.style.SUCCESS(f"{len(parents)} parents relancés."))
