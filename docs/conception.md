# Porte-Voix — Conception

*Porte-Voix* : application de gestion des représentants des parents d'élèves de l'APE. Nom technique du projet Django : `portevoix`.

## 1. Objectif

Automatiser la désignation des représentants des parents d'élèves (collège et lycée) pour supprimer les manipulations manuelles (tableurs, copier-coller, emails à la main), longues et sources d'erreurs.

## 2. Règles de gestion

- Un parent peut se porter candidat pour un ou plusieurs de ses enfants.
- Avant la rentrée, seul le **niveau** est connu (6e, 5e, 4e, 3e, 2de, 1re, Terminale par défaut ; liste modifiable dans l'admin, ex. niveaux professionnels) ; la **classe** (ex. 4D) est connue à la rentrée.
- Un parent peut candidater à tout moment, y compris après la rentrée (même formulaire).
- Un représentant doit avoir au moins un enfant dans la classe.
- **Maximum 4 représentants par classe.**
- Si plus de 4 candidats : priorité aux **adhérents de l'APE**, puis à la **date de candidature**.
- Les candidats non retenus sont placés en **liste d'attente**.
- Un représentant retenu **n'est jamais remplacé** par un candidat arrivé plus tard, même adhérent ; le classement ne s'applique qu'aux places libres et à la liste d'attente.
- Le statut d'adhérent est **vérifié** par rapprochement de l'email avec la liste des adhérents (import CSV, ex. export HelloAsso), jamais auto-déclaré.
- Pas de distinction titulaire / suppléant pour l'instant (ajout d'un champ possible plus tard).

## 3. Parcours

| Étape | Acteur | Déroulement |
|---|---|---|
| Candidature | Parent | Formulaire public → email de confirmation avec **lien magique** (vérifie l'adresse, pas de mot de passe). Un seul lien par parent, identique dans tous les emails, menant à son espace : tous ses enfants, ajout d'un autre enfant, retrait, suppression de ses données. |
| Lien perdu | Parent | Page « Lien perdu ? » (`/lien-perdu/`) : le parent saisit son email et reçoit à nouveau son lien. Même réponse que l'email soit connu ou non (ne révèle pas qui est inscrit). |
| Rentrée | Automatique | Email avec le lien : « indiquez la classe de votre enfant ». La classe est fournie par le parent, pas par l'établissement (évite un transfert de données). |
| Attribution | Automatique | Dès qu'un enfant a une classe : moins de 4 retenus → *retenu*, sinon → *attente* (adhérents d'abord, puis par date). |
| Notification | Automatique | Email « vous êtes représentant de la 4D » + coordonnées des autres représentants de la classe (si consentement) + lien vers le kit. Email aux candidats en attente. |
| Retrait | Parent (via lien) ou administrateur | Parent : bouton « Retirer » par enfant dans son espace → la candidature est **supprimée** (pas de trace conservée, le parent peut se représenter) → promotion automatique du 1er de la liste d'attente, notifié par email. Administrateur : statut *retiré* dans l'admin (sans email ni promotion automatique). |
| Conseil de classe (V3) | Admin saisit les dates | Alerte J-14 aux représentants → chacun indique sa disponibilité via son lien → l'admin voit qui siège. |
| Fin d'année | Commande planifiée | Purge des données de l'année scolaire écoulée. |

Le bureau de l'APE n'intervient que pour : importer le CSV des adhérents, créer la liste des classes à la rentrée, saisir les dates des conseils de classe, retirer un représentant si nécessaire.

## 4. Modèle de données

```
Adherent      email (unique) — remplacé à chaque import CSV
Parent        email (unique), nom, prénom, téléphone (optionnel),
              consentement_le, partage_coordonnees (bool)
Niveau        code (clé, ex. "4", "2PRO"), libellé, ordre — géré dans l'admin
Classe        nom ("4D", unique), niveau → (code le plus long qui débute le nom)
Candidature   parent →, prénom_enfant, niveau →, classe → (vide avant la rentrée),
              statut [candidat | retenu | attente | retiré], date
              contrainte : (parent, classe) unique
-- V3 --
Conseil       classe →, date
Disponibilité conseil →, parent →, disponible (bool)
```

- Une candidature porte directement l'enfant (prénom, niveau) : pas de table enfant séparée.
- Le statut d'adhérent est calculé à la volée en comparant l'email du parent à la table `Adherent` ; un parent inscrit après l'import est donc reconnu.
- Le niveau suffit à distinguer collège (6e–3e) et lycée (2de–Terminale) : pas de table établissement.
- Une seule année scolaire en base : la purge annuelle vide toutes les tables, pas de champ année.
- Les classes sont créées par l'admin à la rentrée (commande `creer_classes`) ; le parent choisit la sienne dans une liste (pas de saisie libre, donc pas de fautes de frappe).
- Données enfant minimisées : prénom, niveau, classe. Pas de date de naissance.

## 5. Architecture

| Composant | Choix | Raison |
|---|---|---|
| Framework | **Django** | Admin (back-office), authentification, emails, migrations, formulaires inclus. |
| Base de données | **SQLite** | Volume faible (quelques centaines de parents) ; sauvegarde = copie d'un fichier ; hébergement simplifié. |
| Authentification parents | **Lien magique** via `django.core.signing` (natif) | Pas de mot de passe, email vérifié, aucune dépendance. |
| Authentification admin | Admin Django + **2FA** (`django-otp`) | Seule dépendance ajoutée, justifiée par les données de mineurs. |
| Emails | **SMTP Gmail** du compte de l'APE (mot de passe d'application) | L'adresse d'expédition est en `@gmail.com` : seul Gmail peut l'envoyer sans tomber en spam (DMARC). Gratuit, ~500 emails/jour. |
| Style des pages | **Pico CSS** (version *classless*), copié dans le projet | Rendu soigné sans classes à écrire ; thème clair/sombre (réglage de l'appareil, ou bouton mémorisé dans le navigateur). Servi localement : aucune requête vers un CDN, donc pas d'adresse IP des parents transmise à un tiers. |
| Tâches planifiées | Commandes `manage.py` lancées par cron | Relance rentrée, alertes conseils, sauvegarde, purge. |
| Kit du parent délégué | PDF statique, lien dans l'email de nomination | Pas de gestion documentaire. |

## 6. Déploiement

**Choix : Alwaysdata, offre gratuite** (0 €, hébergement à Paris).

- 100 Mo d'espace, suffisant pour l'application et SQLite.
- Python/Django supporté nativement, HTTPS, SSH et tâches planifiées (cron) fournis.
- Pas de serveur à maintenir (pas de mises à jour système, pas de configuration TLS).
- Évolution sans changement de code vers l'offre payante (~10 €/mois) si nécessaire.

Annexes :

- **Domaine** : sous-domaine gratuit de l'hébergeur, ou sous-domaine du site de l'APE (~10 €/an pour un domaine propre).
- **Sauvegardes** : copie quotidienne du fichier SQLite par cron, conservée chez l'hébergeur.
- **Évolution** : avec un nom de domaine propre à l'APE, passer à une adresse d'expédition authentifiée (SPF/DKIM) via Brevo ou l'envoi SMTP d'Alwaysdata ; seules les variables `EMAIL_*` changent.

Alternatives écartées :

| Solution | Raison de l'écart |
|---|---|
| Clever Cloud | ~10–20 €/mois, trop cher pour le besoin. |
| VPS Hetzner / OVH (4–6 €/mois) | Demande un administrateur système bénévole et sa relève. |
| PythonAnywhere gratuit | Sortie réseau restreinte (envoi d'emails compromis), société britannique. |
| Render, Railway, Fly, Oracle Free | Sociétés américaines, offres gratuites instables. |
| Tableurs en ligne (Grist, Google Sheets) | Ne répond pas à l'objectif de supprimer les manipulations manuelles. |

Tarifs et limites des offres gratuites à vérifier avant engagement.

## 7. RGPD

- **Responsable de traitement** : l'APE (représentée par sa présidence). Traitement inscrit au **registre des traitements**.
- **Base légale** : consentement, par cases à cocher non pré-cochées :
  1. candidature et traitement des données ;
  2. (distinct) transmission des coordonnées aux autres représentants de la classe et au chef d'établissement.
- **Minimisation** : parent (nom, prénom, email, téléphone optionnel) ; enfant (prénom, niveau, classe).
- **Information (art. 13)** sur le formulaire : finalité, destinataires (bureau APE, chef d'établissement), durée de conservation, droits (accès, rectification, effacement, retrait du consentement), contact.
- **Conservation** : jusqu'à la fin de l'année scolaire, puis purge automatique. Candidats non retenus supprimables plus tôt.
- **Sous-traitants** : Alwaysdata (hébergement, France) et Google (boîte Gmail de l'APE, déjà utilisée) ; DPA (art. 28) acceptés auprès de chacun.
- **Accès** : admin réservé à 2–3 membres du bureau, avec 2FA. Pas d'export de fichiers envoyés par email.
- **Emails groupés** : destinataires en Cci, sauf entre représentants d'une même classe ayant consenti.
- **Droits des personnes** : le parent peut consulter, modifier ou retirer sa candidature via son lien magique.

## 8. Feuille de route

1. **MVP** : formulaire de candidature, lien magique, saisie de la classe, attribution automatique, emails de nomination/attente, admin, import CSV adhérents, purge annuelle.
2. **V2** : retrait par le parent avec promotion depuis la liste d'attente (fait), retrait admin avec promotion, diffusion du kit du parent délégué.
3. **V3** : conseils de classe, saisie des disponibilités par les représentants, alertes avant chaque conseil.
