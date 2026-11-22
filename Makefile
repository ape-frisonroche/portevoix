PY := .venv/bin/python
M  := $(PY) manage.py

.PHONY: help install migrate migrations run test deploy admin classes adherents relance purge shell clean

help: ## Affiche cette aide
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-12s %s\n", $$1, $$2}'

$(PY):
	uv venv

install: $(PY) ## Crée le venv et installe les dépendances
	uv pip install -q -r requirements.txt

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

admin: ## Crée un superutilisateur + code de 1re connexion (2FA)
	$(M) createsuperuser
	@read -p "Identifiant du superutilisateur : " u && $(M) addstatictoken $$u

classes: ## Crée des classes : make classes C="6A 6B 4D TG1"
	$(M) creer_classes $(C)

adherents: ## Importe les adhérents : make adherents F=adherents.csv
	$(M) import_adherents $(F)

relance: ## Envoie l'email de rentrée (affiché dans le terminal en dev)
	$(M) relance_rentree

purge: ## Purge annuelle (demande confirmation)
	@read -p "Supprimer TOUTES les données ? [oui/N] " r && [ "$$r" = oui ] && $(M) purge_annuelle --oui

shell: ## Shell Django
	$(M) shell

clean: ## Supprime la base de dev et les caches
	rm -f db.sqlite3
	find . -path ./.venv -prune -o -name __pycache__ -type d -exec rm -rf {} +
