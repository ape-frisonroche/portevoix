PY := .venv/bin/python
M  := $(PY) manage.py
# chemin de la base (DB_PATH du .env ou db.sqlite3), évalué seulement par backup/restore
DB  = $(shell $(M) shell -v 0 -c "from django.conf import settings; print(settings.DATABASES['default']['NAME'])")
# copie à chaud via l'API backup de SQLite (cohérente même si l'app tourne)
COPIE := $(PY) -c "import sqlite3, sys; sqlite3.connect(sys.argv[1]).backup(sqlite3.connect(sys.argv[2]))"

.PHONY: help install migrate migrations run test deploy admin classes adherents relance purge backup restore update shell clean

help: ## Affiche cette aide
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-12s %s\n", $$1, $$2}'

install: ## Crée le venv et installe les dépendances (pyproject.toml)
	uv sync -q

migrate: ## Applique les migrations
	$(M) migrate

migrations: ## Génère les migrations après modification des modèles
	$(M) makemigrations representants

run: migrate ## Lance le serveur de dev (http://localhost:8000)
	$(M) runserver

test: ## Lance les tests
	$(M) test representants

deploy: install migrate ## Installe, migre et collecte les fichiers statiques (serveur)
	$(M) collectstatic --noinput

update: ## Mise à jour sur le serveur : sauvegarde, git pull, deploy (redémarrer ensuite le site)
	$(MAKE) -s backup
	git pull --ff-only
	$(MAKE) deploy
	uv cache clean -q
	@echo "Pensez à redémarrer le site (Alwaysdata : Web > Sites > Redémarrer)."

admin: ## Crée un superutilisateur (son email reçoit le code de connexion) : make admin U=identifiant
	@test -n "$(U)" || { echo "Usage : make admin U=identifiant"; exit 1; }
	$(M) createsuperuser --username "$(U)"

classes: ## Crée des classes : make classes C="6A 6B 4D TG1"
	$(M) creer_classes $(C)

adherents: ## Importe les adhérents : make adherents F=adherents.csv
	$(M) import_adherents $(F)

relance: ## Envoie l'email de rentrée, tous niveaux ou un seul : make relance N=6
	$(M) relance_rentree $(if $(N),--niveau "$(N)")

purge: ## Purge annuelle (demande confirmation)
	@read -p "Supprimer TOUTES les données ? [oui/N] " r && [ "$$r" = oui ] && $(M) purge_annuelle --oui

backup: ## Sauvegarde la base dans backups/ (ou : make backup F=fichier.sqlite3)
	@mkdir -p backups
	$(COPIE) "$(DB)" "$(or $(F),backups/db-$(shell date +%Y%m%d-%H%M%S).sqlite3)"

restore: ## Restaure une sauvegarde : make restore F=backups/db-....sqlite3 (demande confirmation)
	@test -f "$(F)" || { echo "Fichier introuvable : make restore F=backups/..."; exit 1; }
	@read -p "Remplacer la base par $(F) ? [oui/N] " r && [ "$$r" = oui ]
	$(MAKE) -s backup F=backups/avant-restore-$(shell date +%Y%m%d-%H%M%S).sqlite3
	$(COPIE) "$(F)" "$(DB)"

shell: ## Shell Django
	$(M) shell

clean: ## Supprime la base de dev et les caches
	rm -f db.sqlite3
	find . -path ./.venv -prune -o -name __pycache__ -type d -exec rm -rf {} +
