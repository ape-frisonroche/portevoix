# Porte-Voix

Gestion des parents délégués de l'APE. Conception : [docs/conception.md](docs/conception.md).

## Développement

Prérequis : [uv](https://docs.astral.sh/uv/) (`pip install --user uv`), qui installe aussi Python 3.11+ si besoin.

```bash
make install   # crée .venv et installe les dépendances (pyproject.toml, uv.lock)
make test
make run       # http://localhost:8000/ (accueil ; formulaire sur /candidater/)
```

`make help` liste toutes les commandes. Sans `.env`, l'app tourne en mode debug avec une base `db.sqlite3` locale, et les emails (lien de l'espace parent compris) s'affichent dans le terminal.

Pour essayer le parcours complet en local :

1. `make admin U=admin` : crée un super-utilisateur pour `/admin/` (le code de connexion s'affiche dans le terminal).
2. Candidater sur le formulaire, puis ouvrir le lien affiché dans le terminal.
3. `make classes C="4A 4B"` : crée des classes, pour que le parent puisse choisir la sienne.

Organisation du code :

| Emplacement | Contenu |
|---|---|
| `portevoix/settings.py` | configuration (lue depuis `.env`) |
| `portevoix/admin_site.py`, `representants/templates/admin/code.html` | connexion à l'admin : étape du code reçu par email |
| `representants/models.py` | données : parents, classes, candidatures, adhérents |
| `representants/services.py` | règles métier : attribution des places, emails, lien de l'espace parent |
| `representants/views.py`, `urls.py`, `templates/` | pages publiques (accueil, formulaire, espace parent, lien perdu) |
| `representants/templates/representants/base.html` | gabarit commun : en-tête, bouton clair/sombre, quelques règles CSS maison |
| `representants/static/representants/` | Pico CSS (copie locale, ne pas remplacer par un CDN), logo de l'APE (`logo.svg`, aussi icône d'onglet) |
| `representants/admin.py` | interface d'administration |
| `representants/management/commands/` | commandes `make` (import, relance, purge…) |
| `representants/tests.py` | tests |

Modifications courantes :

- **Dépendances** : `uv add <paquet>` (met à jour `pyproject.toml` et `uv.lock`, à commiter tous les deux).
- **Modèles** (`models.py`) : `make migrations` puis `make migrate`, et commiter le fichier de migration généré.
- **Style** : Pico CSS met en forme le HTML sans classes ; pour un réglage, ajouter une règle dans le `<style>` de `base.html` en utilisant ses variables (`var(--pico-…)`) pour rester compatible clair/sombre. Mettre à jour Pico : remplacer le fichier par la version *classless* (`pico.classless.min.css`) d'une nouvelle version.
- **Version** : champ `version` de `pyproject.toml`.
- **CI** : GitHub Actions (`.github/workflows/ci.yml`) lance les tests et vérifie qu'aucune migration ne manque à chaque push sur `main` et à chaque pull request.

## Administrateurs

L'admin (`/admin/`) se fait en deux étapes : identifiant et mot de passe, puis un **code à 6 chiffres envoyé par email** à l'adresse du compte (valable 5 minutes, au plus un envoi par minute). Rien à installer.

| Rôle | Droits | Qui |
|---|---|---|
| **Super-utilisateur** | tout, y compris les comptes administrateurs | 1 ou 2 personnes (technique, présidence), seules à avoir l'accès SSH aux commandes `make` |
| **Groupe « Bureau »** (créé automatiquement) | parents, classes, candidatures, adhérents, niveaux ; pas de gestion des comptes | les autres membres du bureau |

### Se connecter

1. `/admin/` : identifiant et mot de passe.
2. La page « Code de connexion » indique l'adresse à laquelle le code a été envoyé (objet : « [Porte-Voix] Code de connexion : 123456 »).
3. Saisir le code puis **Valider**. Code expiré ou perdu : lien **Renvoyer un code** (au plus un par minute). Après un code erroné, attendre quelques secondes avant de réessayer (protection contre les essais au hasard).

La sécurité de l'admin repose sur la boîte email de chaque administrateur : utiliser une adresse personnelle, non partagée, protégée par sa propre double authentification.

### Premier super-utilisateur (SSH)

`make admin U=identifiant` : crée le super-utilisateur (renseigner son email : c'est là qu'arrive le code), puis se connecter sur `/admin/`.

### Ajouter un administrateur (par un super-utilisateur, dans `/admin/`)

*Utilisateurs → Ajouter* : identifiant et mot de passe provisoire, puis renseigner son **adresse email**, cocher **Statut équipe** et :
- soit l'ajouter au groupe **Bureau** ;
- soit cocher **Statut super-utilisateur**.

Il change son mot de passe via le lien en haut de l'admin.

### Départ et incidents

- **Export Excel des candidatures** : admin → *Candidatures*, filtrer (statut, niveau, classe) ou rechercher, puis **Exporter (Excel)** : le fichier contient exactement les candidatures affichées. Il contient des données personnelles : ne pas l'envoyer par email ni le conserver au-delà de l'usage.
- **Départ du bureau** (à faire à chaque changement de bureau) : *Utilisateurs* → décocher **Actif**. Effet immédiat.
- **Code non reçu** : vérifier les indésirables, attendre une minute puis **Renvoyer un code** ; sinon un super-utilisateur vérifie l'adresse email du compte dans *Utilisateurs*.
- **Envoi d'emails en panne** : plus personne ne peut se connecter à l'admin (ni recevoir de lien). En SSH, tester avec `.venv/bin/python manage.py sendtestemail mon@adresse.fr`, puis corriger les variables `EMAIL_*` du `.env` (ex. mot de passe d'application Gmail révoqué).
- **Parent ayant perdu son lien** : l'orienter vers la page « Lien perdu ? » (`/lien-perdu/`, accessible depuis le formulaire), qui lui renvoie son lien par email.
- **Sauvegarde / restauration** (SSH, dans `~/portevoix`) : `make backup` copie la base dans `backups/` ; `make restore F=backups/db-3.sqlite3` la remplace par une sauvegarde, après confirmation et après avoir sauvegardé la base actuelle (`backups/avant-restore-…`). Lancer ensuite `make migrate` si la sauvegarde date d'une version antérieure du code.
- **Modifications manuelles** : changer un statut ou supprimer une candidature dans l'admin n'envoie pas d'email et ne promeut pas la liste d'attente. Pour un retrait, préférer que le parent utilise son espace personnel : bouton « Retirer » pour un enfant, ou suppression de toutes ses données ; la place libérée va alors au 1er de la liste d'attente, prévenu par email.

## Calendrier annuel

| Quand | Commande |
|---|---|
| Juin (ouverture) | vérifier les niveaux proposés (admin → *Niveaux*), puis partager l'URL du site (page d'accueil) |
| Après chaque campagne d'adhésion | importer les adhérents (voir [Import des adhérents](#import-des-adhérents-csv)) |
| Rentrée, classes connues | `make classes C="6A 6B 5A ... 2NDE1 1G1 TG1"` (le niveau est le code de niveau qui débute le nom, le plus long l'emportant : 2PRO1 → 2PRO) |
| Rentrée, une fois les classes créées | admin → *Parents* → **Relance de rentrée** : choisir un niveau (ou tous), vérifier la liste des parents ayant un enfant sans classe, puis envoyer leur lien (ou en SSH `make relance`, `make relance N=6`). Utile niveau par niveau quand les listes de classes sortent à des dates différentes ; relançable quelques jours plus tard pour les retardataires. |
| Fin d'année | `make backup`, puis `make purge` |

Les places sont attribuées automatiquement dès qu'un parent indique la classe. Une modification manuelle du statut dans l'admin n'envoie pas d'email.

### Import des adhérents (CSV)

Seuls les emails comptent : un parent est adhérent si son email figure dans la liste (comparaison sans tenir compte des majuscules).

- **Depuis l'admin** (Bureau ou super-utilisateur) : *Adhérents* → **Importer un CSV**. Par défaut les emails sont **ajoutés** à la liste ; cocher « Remplacer toute la liste » pour repartir de zéro (ex. nouvel export complet HelloAsso).
- **En SSH** : `make adherents F=adherents.csv` **remplace** toute la liste. Options : `--colonne "Email payeur"`, `--delimiteur ";"` (via `.venv/bin/python manage.py import_adherents`).

Format accepté :
- n'importe quel export (HelloAsso, tableur…) avec une ligne d'en-tête ; la colonne utilisée est la première dont le nom contient « mail » ;
- séparateur virgule, point-virgule ou tabulation (détecté) ; un fichier d'une seule colonne `email` convient ;
- encodage UTF-8 ou Excel Windows ; les lignes sans « @ » sont ignorées.

Exemple minimal :
```
email
parent1@exemple.fr
parent2@exemple.fr
```

Après chaque import, les places sont recalculées : les adhérents passent devant dans les listes d'attente (un parent déjà retenu n'est jamais remplacé) et les parents concernés reçoivent l'email correspondant.

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

En dev (sans `EMAIL_HOST`), les emails s'affichent dans le terminal (codes de connexion à l'admin compris). En production, deux options : il suffit de changer les variables `EMAIL_*`. Les codes de connexion à l'admin passent par le même envoi que les emails aux parents.

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

Pas de paquet à construire : le serveur récupère le code depuis GitHub, et `make deploy` installe les dépendances, applique les migrations et collecte les fichiers statiques. Dans ce qui suit, `<compte>` est le nom du compte Alwaysdata.

### Installation (une seule fois)

1. **Compte** : créer un compte (l'offre gratuite suffit), puis dans *Environnement → Python* choisir **Python 3.11 ou plus récent**.
2. **Code**, par SSH (`ssh <compte>@ssh-<compte>.alwaysdata.net`) :
   ```bash
   pip install --user uv
   git clone https://github.com/ape-frisonroche/portevoix.git ~/portevoix
   ```
   Dépôt GitHub **privé** : générer une clé sur Alwaysdata (`ssh-keygen -t ed25519`), l'ajouter dans GitHub (*Settings → Deploy keys*, lecture seule), puis cloner avec `git@github.com:ape-frisonroche/portevoix.git`.
3. **Configuration** : `cd ~/portevoix && cp .env.example .env && chmod 600 .env`, puis remplir `.env` (voir [Configuration](#configuration-variables-denvironnement)) : `SECRET_KEY`, `ALLOWED_HOSTS=<compte>.alwaysdata.net`, `SITE_URL=https://<compte>.alwaysdata.net`, `DB_PATH=/home/<compte>/portevoix/db.sqlite3`, variables `EMAIL_*`.
4. **Installation** : `make deploy && uv cache clean`.
5. **Test d'envoi d'email** : `.venv/bin/python manage.py sendtestemail votre@adresse.fr`. Sans emails, ni les parents (liens) ni les administrateurs (code de connexion) ne peuvent rien faire.
6. **Premier administrateur** : `make admin U=<identifiant>`, avec une adresse email personnelle (le code de connexion y est envoyé).
7. **Site** : *Web → Sites → Ajouter* : type **Python WSGI**, application `/home/<compte>/portevoix/portevoix/wsgi.py`, virtualenv `/home/<compte>/portevoix/.venv`, répertoire de travail `/home/<compte>/portevoix`, chemin statique `/static/=staticfiles/`. Pas de variables d'environnement à saisir : elles viennent de `.env`.
8. **Tâche planifiée** (*Tâches planifiées → Ajouter*), sauvegarde quotidienne :
   `cd ~/portevoix && make -s backup F=backups/db-$(date +%u).sqlite3`
   (7 copies tournantes, une par jour de la semaine).

### Mise à jour

```bash
cd ~/portevoix && make update
```

`make update` sauvegarde la base, récupère le code (`git pull`), lance `make deploy` (dépendances, migrations, fichiers statiques) puis vide le cache de `uv`. **Redémarrer ensuite le site** (*Web → Sites → Redémarrer*) pour charger le nouveau code. En cas de problème : `make restore F=backups/db-….sqlite3` avec la sauvegarde faite au début de la mise à jour.

### Offre gratuite

- **Espace disque limité** (de l'ordre de 100 Mo) : l'environnement Python (`.venv`) en prend quelques dizaines ; `make update` vide le cache de `uv`, et les sauvegardes sont limitées à 7 copies. Vérifier l'espace utilisé dans l'interface Alwaysdata.
- Préférer le Python fourni par Alwaysdata (étape 1) : si `uv` doit en télécharger un, il occupe aussi de l'espace.
- Vérifier les limites exactes de l'offre dans la documentation Alwaysdata ; les libellés de l'interface peuvent aussi varier.

## Licence

Ce projet est distribué sous licence [GNU GPL v3](LICENSE).
