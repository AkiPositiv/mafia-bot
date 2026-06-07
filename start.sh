#!/bin/bash
set -e

echo ">>> Running Alembic migrations..."
alembic upgrade head
echo ">>> Migrations done."

echo ">>> Starting Game Bot..."
python game_bot.py &
GAME_PID=$!

echo ">>> Starting Admin Bot..."
python admin_bot.py &
ADMIN_PID=$!

echo ">>> Both bots running. game_pid=$GAME_PID admin_pid=$ADMIN_PID"

# Ждём завершения любого из процессов
wait -n $GAME_PID $ADMIN_PID
EXIT_CODE=$?

echo ">>> One of the bots exited (code $EXIT_CODE). Stopping both."
kill $GAME_PID $ADMIN_PID 2>/dev/null || true
exit $EXIT_CODE
