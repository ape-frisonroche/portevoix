# Porte-Voix

Gestion des représentants des parents d'élèves de l'APE. Conception : [docs/conception.md](docs/conception.md).

## Développement

Prérequis : [uv](https://docs.astral.sh/uv/) (`pip install --user uv`), qui installe aussi Python 3.11+ si besoin.

```bash
make install   # crée .venv et installe les dépendances (pyproject.toml, uv.lock)
make test
make run       # http://localhost:8000/ (formulaire parents)
```

`make help` liste toutes les commandes. Sans `.env`, l'app tourne en mode debug avec une base `db.sqlite3` locale, et les emails (lien de l'espace parent compris) s'affichent dans le terminal.

Pour essayer le parcours complet en local :

1. `make admin` : crée un super-utilisateur et son code de première connexion pour `/admin/`.
2. Candidater sur le formulaire, puis ouvrir le lien affiché dans le terminal.
3. `make classes C="4A 4B"` : crée des classes, pour que le parent puisse choisir la sienne.

Organisation du code :

| Emplacement | Contenu |
|---|---|
| `portevoix/settings.py` | configuration (lue depuis `.env`) |
| `representants/models.py` | données : parents, classes, candidatures, adhérents |
| `representants/services.py` | règles métier : attribution des places, emails, lien de l'espace parent |
| `representants/views.py`, `urls.py`, `templates/` | pages publiques (formulaire, espace parent, lien perdu) |
| `representants/admin.py` | interface d'administration |
| `representants/management/commands/` | commandes `make` (import, relance, purge…) |
| `representants/tests.py` | tests |

Modifications courantes :

- **Dépendances** : `uv add <paquet>` (met à jour `pyproject.toml` et `uv.lock`, à commiter tous les deux).
- **Modèles** (`models.py`) : `make migrations` puis `make migrate`, et commiter le fichier de migration généré.
- **Version** : champ `version` de `pyproject.toml`.
- **CI** : GitHub Actions (`.github/workflows/ci.yml`) lance les tests et vérifie qu'aucune migration ne manque à chaque push sur `main` et à chaque pull request.

## Administrateurs

L'admin (`/admin/`) exige un mot de passe **et** un code à 6 chiffres généré par une application d'authentification (ex. Aegis, FreeOTP, Google Authenticator).

| Rôle | Droits | Qui |
|---|---|---|
| **Super-utilisateur** | tout, y compris les comptes administrateurs | 1 ou 2 personnes (technique, présidence), seules à avoir l'accès SSH aux commandes `make` |
| **Groupe « Bureau »** (créé automatiquement) | parents, classes, candidatures, adhérents ; pas de gestion des comptes | les autres membres du bureau |

### Premier super-utilisateur (SSH)

`make admin` : crée le super-utilisateur et affiche un code à usage unique pour la première connexion.

1. Se connecter sur `/admin/` avec ce code dans le champ « OTP Token ».
2. *TOTP devices* → *Ajouter* → choisir son utilisateur → enregistrer.
3. Dans la liste, cliquer sur le lien *qrcode* et le scanner avec l'application d'authentification.
4. *Static devices* : supprimer le code de première connexion.

### Ajouter un administrateur (par un super-utilisateur, dans `/admin/`)

1. *Utilisateurs → Ajouter* : identifiant et mot de passe provisoire, puis cocher **Statut équipe** et :
   - soit ajouter au groupe **Bureau** ;
   - soit cocher **Statut super-utilisateur**.
2. *Static devices → Ajouter* : choisir l'utilisateur, ajouter un code de première connexion. Transmettre mot de passe et code par deux canaux différents (ex. email et SMS).
3. Enregistrement de l'application d'authentification :
   - **super-utilisateur** : il le fait lui-même après sa première connexion (étapes 2 à 4 ci-dessus) ;
   - **Bureau** : il n'a pas accès aux *TOTP devices*. Un super-utilisateur crée l'appareil pour lui ; le nouvel administrateur scanne le *qrcode* sur l'écran du super-utilisateur (en personne ou en partage d'écran).
4. Supprimer son code de première connexion (*Static devices*). Il change son mot de passe via le lien en haut de l'admin.

### Départ et incidents

- **Départ du bureau** (à faire à chaque changement de bureau) : *Utilisateurs* → décocher **Actif**. Effet immédiat.
- **Téléphone perdu** : supprimer son appareil dans *TOTP devices*, lui donner un nouveau code de première connexion, puis recommencer l'enregistrement.
- **Parent ayant perdu son lien** : l'orienter vers la page « Lien perdu ? » (`/lien-perdu/`, accessible depuis le formulaire), qui lui renvoie son lien par email.
- **Sauvegarde / restauration** (SSH, dans `~/portevoix`) : `make backup` copie la base dans `backups/` ; `make restore F=backups/db-3.sqlite3` la remplace par une sauvegarde, après confirmation et après avoir sauvegardé la base actuelle (`backups/avant-restore-…`). Lancer ensuite `make migrate` si la sauvegarde date d'une version antérieure du code.
- **Modifications manuelles** : changer un statut ou supprimer une candidature dans l'admin n'envoie pas d'email et ne promeut pas la liste d'attente. Pour un retrait, préférer que le parent utilise son espace personnel : bouton « Retirer » pour un enfant, ou suppression de toutes ses données ; la place libérée va alors au 1er de la liste d'attente, prévenu par email.

## Calendrier annuel

| Quand | Commande |
|---|---|
| Juin (ouverture) | partager l'URL du formulaire |
| Après chaque campagne d'adhésion | `make adherents F=adherents.csv` (colonne email détectée automatiquement) |
| Rentrée, classes connues | `make classes C="6A 6B 5A ... 2NDE1 1G1 TG1"` (le 1er caractère donne le niveau) |
| Rentrée | `make relance` |
| Fin d'année | `make backup`, puis `make purge` |

Les places sont attribuées automatiquement dès qu'un parent indique la classe. Une modification manuelle du statut dans l'admin n'envoie pas d'email.

## Configuration (variables d'environnement)

En dev, rien à configurer : les valeurs par défaut suffisent.

En production, les variables sont lues dans le fichier `.env` à la racine du projet, pour le site comme pour les commandes `make` et les tâches planifiées. Une variable déjà définie dans l'environnement est prioritaire sur `.env`.

```bash
cp .env.example .env && chmod 600 .env   # puis remplir .env
```

`.env` contient la clé secrète et le mot de passe d'envoi : il n'est jamais versionné (voir `.gitignore`).

| Variable | Exemple |
|---|---|
| `DEBUG` | `0` en production |
| `SECRET_KEY` | longue chaîne aléatoire (`python -c "import secrets; print(secrets.token_urlsafe(50))"`) |
| `ALLOWED_HOSTS` | `portevoix.alwaysdata.net` |
| `SITE_URL` | `https://portevoix.alwaysdata.net` |
| `DB_PATH` | `/home/<compte>/portevoix/db.sqlite3` |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL` | voir [Emails](#emails) |
| `KIT_URL` | lien vers le PDF du kit du parent délégué |
| `CONTACT_RGPD` | email de contact affiché sur le formulaire |

## Emails

En dev (sans `EMAIL_HOST`), les emails s'affichent dans le terminal. En production, deux options : il suffit de changer les variables `EMAIL_*`.

### Gmail (choix actuel)

Pour une adresse d'expédition en `@gmail.com` : seul Gmail peut l'envoyer sans tomber en spam.

| Variable | Valeur |
|---|---|
| `EMAIL_HOST`, `EMAIL_PORT` | `smtp.gmail.com`, `587` |
| `EMAIL_HOST_USER` | adresse Gmail de l'APE |
| `EMAIL_HOST_PASSWORD` | mot de passe d'application Google |
| `DEFAULT_FROM_EMAIL` | `Porte-Voix <ape.exemple@gmail.com>` (la même adresse) |

1. Sur le compte Google de l'APE, activer la validation en deux étapes.
2. *Compte Google → Sécurité → Mots de passe des applications* : en créer un pour « Porte-Voix ».
3. Le renseigner dans `EMAIL_HOST_PASSWORD`. Il peut être révoqué à tout moment sans toucher au compte.

Quota : environ 500 emails par jour (à vérifier). Au-delà, les envois échouent jusqu'au lendemain : attention à `make relance` s'il y a beaucoup de candidats.

### Brevo (si l'APE a son propre nom de domaine)

Nécessite une adresse d'expédition sur un domaine de l'APE (ex. `contact@ape-exemple.fr`) : Brevo n'est pas adapté à une adresse `@gmail.com`.

1. Créer un compte Brevo (gratuit) et accepter le contrat de sous-traitance RGPD (DPA).
2. *Expéditeurs et domaines* : ajouter le domaine, puis créer chez le registrar les enregistrements DNS fournis (SPF, DKIM, DMARC).
3. *SMTP & API* : générer une clé SMTP.

| Variable | Valeur |
|---|---|
| `EMAIL_HOST`, `EMAIL_PORT` | `smtp-relay.brevo.com`, `587` |
| `EMAIL_HOST_USER` | identifiant SMTP fourni par Brevo |
| `EMAIL_HOST_PASSWORD` | clé SMTP Brevo |
| `DEFAULT_FROM_EMAIL` | `Porte-Voix <contact@ape-exemple.fr>` (adresse du domaine authentifié) |

Quota de l'offre gratuite : 300 emails par jour (à vérifier). Mettre à jour le registre des traitements : Brevo devient sous-traitant.

## Déploiement sur Alwaysdata

1. Créer un compte gratuit, puis copier le code par SSH (ou `git clone`) dans `~/portevoix`.
2. Par SSH, dans `~/portevoix` : créer `.env` (voir [Configuration](#configuration-variables-denvironnement)), puis `make deploy` (à relancer après chaque mise à jour du code ; nécessite `uv`, installable avec `pip install --user uv`).
3. *Web → Sites → Ajouter* : type **Python WSGI**, application `~/portevoix/portevoix/wsgi.py`, virtualenv `~/portevoix/.venv`, répertoire de travail `~/portevoix`, chemin statique `/static/=staticfiles/`. Pas de variables d'environnement à saisir : elles viennent de `.env`.
4. *Tâches planifiées* : sauvegarde quotidienne
   `cd ~/portevoix && make -s backup F=backups/db-$(date +%u).sqlite3`
   (7 copies tournantes, une par jour de la semaine).

Les libellés de l'interface Alwaysdata peuvent varier : vérifiez-les dans leur documentation.

## Licence

Ce projet est distribué sous licence [GNU GPL v3](LICENSE).
