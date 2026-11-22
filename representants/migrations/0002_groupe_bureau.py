"""Crée le groupe « Bureau » : gestion des données de l'application, sans gestion des comptes."""

from django.contrib.auth.management import create_permissions
from django.db import migrations


def creer_groupe(apps, schema_editor):
    # Les permissions ne sont créées qu'après les migrations : on force leur création ici.
    for app_config in apps.get_app_configs():
        app_config.models_module = True
        create_permissions(app_config, apps=apps, verbosity=0)
        app_config.models_module = None

    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    bureau, _ = Group.objects.get_or_create(name="Bureau")
    bureau.permissions.set(Permission.objects.filter(content_type__app_label="representants"))


def supprimer_groupe(apps, schema_editor):
    apps.get_model("auth", "Group").objects.filter(name="Bureau").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("representants", "0001_initial"),
        ("auth", "0012_alter_user_first_name_max_length"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [migrations.RunPython(creer_groupe, supprimer_groupe)]
