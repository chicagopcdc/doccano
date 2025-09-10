#!/usr/bin/env bash
set -euo pipefail

# Resolve project root from this script's location
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

COMPOSE_FILE="${PROJECT_ROOT}/docker/docker-compose.local.yml"
ENV_FILE="${PROJECT_ROOT}/docker/.env"

# Pick compose CLI
if docker compose version >/dev/null 2>&1; then
  DC_BIN="docker compose"
else
  DC_BIN="docker-compose"
fi

dc() { ${DC_BIN} -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" "$@"; }

# Allow both: "./tools/local.sh full" and "./tools/local.sh -task full"
TASK="${1:-help}"
if [[ "${TASK}" == "-task" || "${TASK}" == "--task" ]]; then
  shift || true
  TASK="${1:-help}"
fi

user_admin() {
  # Run migrations first (safe to re-run)
  dc exec backend bash -lc "python manage.py migrate --noinput || true"

  # User roles + ensure admin (all inside Django via manage.py shell)
  dc exec -T backend bash -lc 'cd /backend || true; python manage.py shell <<'"'"'PY'"'"'
import os
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction

# --- User roles ---
try:
    from roles.models import Role
except Exception as e:
    print(f"Roles app not available: {e}")
else:
    names = []
    for attr in dir(settings):
        if attr.startswith("ROLE_"):
            val = getattr(settings, attr)
            if isinstance(val, str) and val:
                names.append(val)
    names = sorted(set(names))
    created_any = False
    with transaction.atomic():
        for name in names:
            _, created = Role.objects.get_or_create(name=name)
            if created:
                created_any = True
                print(f"Created role: {name}")
    if not names:
        print("No ROLE_* constants found; nothing to User.")
    elif not created_any:
        print("All roles already present.")

# --- Ensure admin ---
u = os.environ.get("DJANGO_SUPERUSER_USERNAME") or os.environ.get("ADMIN_USERNAME")
e = os.environ.get("DJANGO_SUPERUSER_EMAIL")    or os.environ.get("ADMIN_EMAIL")
p = os.environ.get("DJANGO_SUPERUSER_PASSWORD") or os.environ.get("ADMIN_PASSWORD")

if not all([u, e, p]):
    print("Admin env missing; skipping superuser creation.")
else:
    User = get_user_model()
    with transaction.atomic():
        obj, created = User.objects.get_or_create(username=u, defaults={"email": e})
        if created:
            obj.set_password(p)
            obj.is_superuser = True
            obj.is_staff = True
            obj.email = e
            obj.save()
            print(f"Created superuser: {u}")
        else:
            changed = False
            if not obj.is_superuser: obj.is_superuser = True; changed = True
            if not obj.is_staff:     obj.is_staff = True;     changed = True
            if e and obj.email != e: obj.email = e;           changed = True
            if changed:
                obj.save()
                print(f"Updated existing user to superuser: {u}")
            else:
                print(f"Superuser exists: {u}")
PY'
}

case "${TASK}" in
  help|-h|--help)
    cat <<'USAGE'
Usage: tools/local.sh <task>

Core:
  full               Build backend+frontend, up -d, migrate, User admin + roll
  up                 Start all services in the background
  down               Stop all services
  clean              down -v (remove DB/media volumes)
  purge              down -v --rmi local (also remove locally built images)
  purge-all          down -v --rmi all (also remove pulled images)
  restart            Restart all services
  ps|status          Show container status
  logs               Follow logs for all services
  logs-backend       Follow backend logs
  logs-nginx         Follow nginx logs

Dev loops:
  fe|rebuild-frontend  Build only frontend image and restart nginx
  be|rebuild-backend   Build only backend image and restart backend

Ops:
  migrate            Run Django migrations
  User-admin         Create/ensure admin from env
  createsuperuser    Run Django createsuperuser (interactive)
  shell-backend      Open a bash shell in the backend container
  shell-nginx        Open a sh shell in the nginx container
  reset              down -v (deletes volumes: DB, media, etc.)

Examples:
  tools/local.sh full
  tools/local.sh fe
  tools/local.sh be
  tools/local.sh logs-backend
  tools/local.sh User-admin
USAGE
    ;;

  full)
    echo "Building backend & frontend..."
    dc build backend nginx
    echo "Starting..."
    dc up -d
    echo "Running..."
    dc exec backend bash -lc "python manage.py migrate --noinput || true"
    echo "User + Role..."
    user_admin
    echo "Full start done. Open http://127.0.0.1/"
    ;;

  up)
    dc up -d
    ;;

  down)
    dc down
    ;;

  restart)
    dc restart
    ;;

  ps|status)
    dc ps
    ;;

  logs)
    dc logs -f
    ;;

  logs-backend)
    dc logs -f backend
    ;;

  logs-nginx)
    dc logs -f nginx
    ;;

  fe|rebuild-frontend)
    echo "Rebuilding frontend (nginx image)..."
    dc build nginx
    echo "Restarting nginx..."
    dc up -d nginx
    ;;

  be|rebuild-backend)
    echo "Rebuilding backend..."
    dc build backend
    echo "Restarting backend..."
    dc up -d backend
    echo "Running migrations & ensuring admin + rolls..."
    user_admin
    ;;

  migrate)
    dc exec backend bash -lc "python manage.py migrate"
    ;;

  User-admin)
    user_admin
    ;;

  createsuperuser)
    dc exec backend bash -lc "python manage.py createsuperuser"
    ;;

  shell-backend)
    dc exec backend bash
    ;;

  shell-nginx)
    dc exec nginx sh
    ;;

  reset)
    echo "This will remove volumes (DB/media). Ctrl-C to cancel."
    sleep 2
    dc down -v
    ;;

  clean)
    echo "This removes all volumes (DB/media). Ctrl-C to cancel."
    sleep 2
    dc down -v --remove-orphans
    ;;

  purge)
    echo "This removes volumes and locally built images. Ctrl-C to cancel."
    sleep 2
    dc down -v --rmi local --remove-orphans
    ;;

  purge-all)
    echo "This removes volumes and ALL images used by services (including pulled). Ctrl-C to cancel."
    sleep 2
    dc down -v --rmi all --remove-orphans
    ;;

  *)
    echo "Unknown task: ${TASK}"
    echo "Run 'tools/local.sh help' for usage."
    exit 1
    ;;
esac
