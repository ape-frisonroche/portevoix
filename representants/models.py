from django.db import models

class Niveau(models.Model):
    """Niveaux proposés aux parents, gérés dans l'admin (ex. ajouter « 2PRO » / « 2de pro »)."""

    code = models.CharField(
        max_length=10, primary_key=True,
        help_text="Début des noms de classe de ce niveau : 4 pour 4A, 2PRO pour 2PRO1. Non modifiable ensuite.",
    )
    libelle = models.CharField("libellé", max_length=50)
    ordre = models.PositiveSmallIntegerField(default=0, help_text="Ordre d'affichage dans les listes.")

    class Meta:
        ordering = ["ordre", "code"]
        verbose_name_plural = "niveaux"

    def __str__(self):
        return self.libelle

    @classmethod
    def depuis_nom_de_classe(cls, nom):
        """Niveau dont le code est le plus long préfixe du nom : 2PRO1 → 2PRO plutôt que 2."""
        codes = [c for c in cls.objects.values_list("code", flat=True) if nom.upper().startswith(c.upper())]
        return cls.objects.get(code=max(codes, key=len)) if codes else None


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
        help_text="avec les autres parents délégués de la classe et l'établissement",
    )

    def __str__(self):
        return f"{self.prenom} {self.nom} <{self.email}>"

    @property
    def adherent(self):
        return Adherent.objects.filter(email__iexact=self.email).exists()


class Classe(models.Model):
    nom = models.CharField(max_length=20, unique=True)
    niveau = models.ForeignKey(Niveau, on_delete=models.PROTECT, related_name="classes")

    class Meta:
        ordering = ["niveau__ordre", "nom"]

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
    niveau = models.ForeignKey(Niveau, on_delete=models.PROTECT, related_name="candidatures")
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
        return f"{self.parent} pour {self.prenom_enfant} ({self.classe or self.niveau})"
