from django.db import models

NIVEAUX = [
    ("6", "6e"), ("5", "5e"), ("4", "4e"), ("3", "3e"),
    ("2", "2de"), ("1", "1re"), ("T", "Terminale"),
]


class Adherent(models.Model):
    """Emails des adhérents de l'APE, remplacés à chaque import CSV."""

    email = models.EmailField(unique=True)

    def __str__(self):
        return self.email


class Parent(models.Model):
    email = models.EmailField(unique=True)
    prenom = models.CharField("prénom", max_length=100)
    nom = models.CharField(max_length=100)
    telephone = models.CharField("téléphone", max_length=20, blank=True)
    consentement_le = models.DateTimeField("consentement au traitement le")
    partage_coordonnees = models.BooleanField(
        "accepte le partage de ses coordonnées", default=False,
        help_text="avec les autres représentants de la classe et l'établissement",
    )

    def __str__(self):
        return f"{self.prenom} {self.nom} <{self.email}>"

    @property
    def adherent(self):
        return Adherent.objects.filter(email__iexact=self.email).exists()


class Classe(models.Model):
    nom = models.CharField(max_length=20, unique=True)
    niveau = models.CharField(max_length=1, choices=NIVEAUX)

    class Meta:
        ordering = ["niveau", "nom"]

    def __str__(self):
        return self.nom


class Candidature(models.Model):
    CANDIDAT, RETENU, ATTENTE, RETIRE = "candidat", "retenu", "attente", "retire"
    STATUTS = [
        (CANDIDAT, "Candidat (classe inconnue)"),
        (RETENU, "Retenu"),
        (ATTENTE, "Liste d'attente"),
        (RETIRE, "Retiré"),
    ]

    parent = models.ForeignKey(Parent, on_delete=models.CASCADE, related_name="candidatures")
    prenom_enfant = models.CharField("prénom de l'enfant", max_length=100)
    niveau = models.CharField(max_length=1, choices=NIVEAUX)
    classe = models.ForeignKey(
        Classe, on_delete=models.PROTECT, null=True, blank=True, related_name="candidatures"
    )
    statut = models.CharField(max_length=10, choices=STATUTS, default=CANDIDAT)
    cree_le = models.DateTimeField("candidature le", auto_now_add=True)

    class Meta:
        ordering = ["cree_le"]
        constraints = [
            # un parent ne représente qu'une fois une même classe
            models.UniqueConstraint(fields=["parent", "classe"], name="un_parent_par_classe"),
        ]

    def __str__(self):
        return f"{self.parent} pour {self.prenom_enfant} ({self.classe or self.get_niveau_display()})"
