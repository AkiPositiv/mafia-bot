#!/bin/bash
# ─────────────────────────────────────────────
# docker_reset.sh — полный сброс Docker окружения
# Останавливает контейнеры, удаляет volumes (базу данных),
# образы проекта и пересобирает всё с нуля.
# ─────────────────────────────────────────────

set -e
cd "$(dirname "$0")/.."   # переходим в корень проекта (mafia/)

echo "==> Stopping and removing containers + volumes..."
docker compose down -v --remove-orphans

echo "==> Removing project images..."
docker compose down --rmi local 2>/dev/null || true

echo "==> Pruning dangling images (optional)..."
docker image prune -f

echo "==> Starting fresh..."
docker compose up -d --build

echo ""
echo "✅ Done! Waiting for postgres to be ready..."
sleep 5
docker compose ps
