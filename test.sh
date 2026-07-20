```bash
#!/usr/bin/env bash

set -euo pipefail

BASE_DIR="/it/itadm/appli"

REPO_URL="${1:-}"
VERSION="${2:-}"

# ------------------------------------------------------------
# Affichage de l'aide
# ------------------------------------------------------------
usage() {
    echo "Usage : $0 <lien-gitlab> <tag-branche-ou-commit>"
    echo ""
    echo "Exemple :"
    echo "  $0 git@gitlab.entreprise.local:data/mon-etl.git v1.0.0"
}

# ------------------------------------------------------------
# Vérification des paramètres
# ------------------------------------------------------------
if [ -z "$REPO_URL" ] || [ -z "$VERSION" ]; then
    echo "Erreur : le lien GitLab et la version sont obligatoires."
    echo ""
    usage
    exit 1
fi

# Exemple :
# git@gitlab.entreprise.local:data/mon-etl.git
# devient :
# mon-etl
APP_NAME=$(basename "$REPO_URL" .git)
APP_DIR="${BASE_DIR}/${APP_NAME}"

echo "============================================"
echo "Préparation du projet"
echo "============================================"
echo "Application : $APP_NAME"
echo "Dépôt      : $REPO_URL"
echo "Version    : $VERSION"
echo "Répertoire : $APP_DIR"
echo "============================================"

# ------------------------------------------------------------
# Clonage du dépôt
# ------------------------------------------------------------
if [ ! -d "$APP_DIR/.git" ]; then
    echo "Clonage du dépôt GitLab..."

    mkdir -p "$BASE_DIR"
    git clone "$REPO_URL" "$APP_DIR"
else
    echo "Le dépôt existe déjà localement."
fi

cd "$APP_DIR"

# ------------------------------------------------------------
# Récupération de la version demandée
# ------------------------------------------------------------
echo "Récupération des branches et des tags..."
git fetch --all --tags --prune

# Annule seulement les modifications des fichiers suivis par Git.
# Les fichiers locaux non suivis, comme un fichier .env, sont conservés.
git reset --hard HEAD

# Vérifie que la version existe bien.
if ! git rev-parse --verify "${VERSION}^{commit}" >/dev/null 2>&1; then
    echo "Erreur : la version '$VERSION' est introuvable."
    exit 1
fi

echo "Sélection de la version : $VERSION"
git checkout --force "$VERSION"

echo "Commit sélectionné :"
git log -1 --oneline

# ------------------------------------------------------------
# Recherche des fichiers Docker
# ------------------------------------------------------------
DOCKERFILE_FOUND="false"
COMPOSE_FOUND="false"

if [ -f "Dockerfile" ]; then
    DOCKERFILE_FOUND="true"
fi

if [ -f "compose.yaml" ]     || \
   [ -f "compose.yml" ]      || \
   [ -f "docker-compose.yml" ] || \
   [ -f "docker-compose.yaml" ]; then
    COMPOSE_FOUND="true"
fi

# ------------------------------------------------------------
# Cas 1 : Dockerfile et Compose existent
# ------------------------------------------------------------
if [ "$DOCKERFILE_FOUND" = "true" ] && \
   [ "$COMPOSE_FOUND" = "true" ]; then

    echo ""
    echo "Le Dockerfile et le fichier Compose existent déjà."
    echo "Aucun fichier Docker n'a été créé."

# ------------------------------------------------------------
# Cas 2 : aucun fichier Docker n'existe
# ------------------------------------------------------------
elif [ "$DOCKERFILE_FOUND" = "false" ] && \
     [ "$COMPOSE_FOUND" = "false" ]; then

    echo ""
    echo "Aucun Dockerfile ni fichier Compose n'a été trouvé."
    echo "Lancement de docker init..."

    # Vérifie que docker init est disponible.
    if ! docker init --help >/dev/null 2>&1; then
        echo "Erreur : la commande 'docker init' n'est pas disponible."
        echo ""
        echo "Docker init doit être installé sur cette machine."
        echo "Il peut aussi être nécessaire de créer manuellement :"
        echo "  - Dockerfile"
        echo "  - compose.yaml"
        echo "  - .dockerignore"
        exit 1
    fi

    # docker init pose des questions à l'utilisateur.
    docker init

# ------------------------------------------------------------
# Cas 3 : un seul des deux fichiers existe
# ------------------------------------------------------------
else
    echo ""
    echo "Erreur : la configuration Docker est incomplète."

    if [ "$DOCKERFILE_FOUND" = "false" ]; then
        echo "Fichier manquant : Dockerfile"
    fi

    if [ "$COMPOSE_FOUND" = "false" ]; then
        echo "Fichier manquant : compose.yaml ou docker-compose.yml"
    fi

    echo ""
    echo "docker init n'a pas été lancé pour éviter d'écraser"
    echo "le fichier Docker qui existe déjà."
    exit 1
fi

# ------------------------------------------------------------
# Contrôle final
# ------------------------------------------------------------
echo ""
echo "Vérification finale..."

FINAL_ERROR="false"

if [ ! -f "Dockerfile" ]; then
    echo "Erreur : aucun Dockerfile n'est présent."
    FINAL_ERROR="true"
fi

if [ ! -f "compose.yaml" ]       && \
   [ ! -f "compose.yml" ]        && \
   [ ! -f "docker-compose.yml" ] && \
   [ ! -f "docker-compose.yaml" ]; then

    echo "Erreur : aucun fichier Compose n'est présent."
    FINAL_ERROR="true"
fi

if [ "$FINAL_ERROR" = "true" ]; then
    exit 1
fi

echo ""
echo "============================================"
echo "Préparation terminée"
echo "============================================"
echo "Projet       : $APP_NAME"
echo "Version      : $VERSION"
echo "Emplacement  : $APP_DIR"
echo ""
echo "Aucune image Docker n'a été construite."
echo "Aucun conteneur Docker n'a été lancé."
echo "============================================"
```
