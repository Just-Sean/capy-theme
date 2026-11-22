#!/usr/bin/env bash
# wt-env.sh — run once inside a fresh git worktree before an agent starts work.
# Gives the worktree its own virtualenv, and (for a project with a .env) its own
# dev-server port so parallel agents don't collide on it.
set -euo pipefail
uv sync
if [ -f .env ]; then
  name=$(basename "$PWD" | tr -c 'a-z0-9\n' '_')
  port=$(( 8001 + $(printf '%s' "$name" | cksum | cut -d' ' -f1) % 900 ))
  if grep -q '^PORT=' .env; then
    sed -i -E "s/^PORT=.*/PORT=${port}/" .env
  else
    printf 'PORT=%s\n' "$port" >> .env
  fi
  # Projects with a SHARED Postgres: also give this worktree its own database so
  # agents don't write to each other's data. Uncomment and adjust to your setup:
  #   sed -i -E "s/^DB_NAME=.*/DB_NAME=app_${name}/" .env
  #   docker compose exec -T db createdb -U postgres "app_${name}" 2>/dev/null || true
  #   uv run python manage.py migrate
  echo "worktree=${name} port=${port} (.env updated; set DB_NAME too if you share one DB)"
else
  # Reusable app: its tests use an in-memory SQLite database, already isolated per
  # process, so parallel worktrees need nothing beyond their own venv.
  echo "worktree ready (uv sync done; tests use isolated in-memory SQLite)"
fi
