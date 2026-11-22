"""Niveaux gérés dans l'admin au lieu d'une liste figée dans le code.

Les anciens codes (6, 5, ..., T) deviennent des lignes Niveau : les données existantes
restent valides car la clé du niveau est son code.
"""

import importlib

import django.db.models.deletion
from django.db import migrations, models

NIVEAUX = [("6", "6e"), ("5", "5e"), ("4", "4e"), ("3", "3e"), ("2", "2de"), ("1", "1re"), ("T", "Terminale")]


def creer_niveaux(apps, schema_editor):
    Niveau = apps.get_model("representants", "Niveau")
    for ordre, (code, libelle) in enumerate(NIVEAUX):
        Niveau.objects.get_or_create(code=code, defaults={"libelle": libelle, "ordre": ordre * 10})


def droits_bureau(apps, schema_editor):
    # le Bureau gère aussi les niveaux : on réapplique la migration du groupe
    importlib.import_module("representants.migrations.0002_groupe_bureau").creer_groupe(apps, schema_editor)


class Migration(migrations.Migration):

    dependencies = [
        ('representants', '0002_groupe_bureau'),
    ]

    operations = [
        migrations.CreateModel(
            name='Niveau',
            fields=[
                ('code', models.CharField(help_text='Début des noms de classe de ce niveau : 4 pour 4A, 2PRO pour 2PRO1. Non modifiable ensuite.', max_length=10, primary_key=True, serialize=False)),
                ('libelle', models.CharField(max_length=50, verbose_name='libellé')),
                ('ordre', models.PositiveSmallIntegerField(default=0, help_text="Ordre d'affichage dans les listes.")),
            ],
            options={
                'ordering': ['ordre', 'code'],
            },
        ),
        migrations.RunPython(creer_niveaux, migrations.RunPython.noop),
        migrations.AlterModelOptions(
            name='classe',
            options={'ordering': ['niveau__ordre', 'nom']},
        ),
        migrations.AlterField(
            model_name='candidature',
            name='niveau',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='candidatures', to='representants.niveau'),
        ),
        migrations.AlterField(
            model_name='classe',
            name='niveau',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='classes', to='representants.niveau'),
        ),
        migrations.RunPython(droits_bureau, migrations.RunPython.noop),
    ]
