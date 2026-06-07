#!/bin/bash
set -e

echo ">>> DATABASE_URL = ${DATABASE_URL:0:40}..."

# Ждём пока PostgreSQL поднимется (Railway стартует сервисы параллельно)
echo ">>> Waiting for database..."
MAX_RETRIES=30
for i in $(seq 1 $MAX_RETRIES); do
    python -c "
import asyncio, asyncpg, os, sys
url = os.environ.get('DATABASE_URL','')
url = url.replace('postgresql+asyncpg://', 'postgresql://')
async def check():
    try:
        conn = await asyncpg.connect(url, timeout=5)
        await conn.close()
    except Exception as e:
        print(f'DB not ready: {e}', flush=True)
        sys.exit(1)
asyncio.run(check())
" && break
    echo ">>> Attempt $i/$MAX_RETRIES failed, retrying in 2s..."
    sleep 2
done

echo ">>> Database is ready."

echo ">>> Running Alembic migrations..."
alembic upgrade head
echo ">>> Migrations done."

echo ">>> Starting Game Bot..."
python game_bot.py &
GAME_PID=$!

echo ">>> Starting Admin Bot..."
# Admin Bot падение не должно убивать Game Bot
python admin_bot.py &
ADMIN_PID=$!

echo ">>> Both bots running. game_pid=$GAME_PID admin_pid=$ADMIN_PID"

# Следим только за Game Bot — он главный
# Если admin_bot упадёт, логируем и продолжаем
monitor_admin() {
    wait $ADMIN_PID 2>/dev/null
    echo ">>> Admin Bot exited (will not restart game_bot)"
}
monitor_admin &

# Контейнер живёт пока жив Game Bot
wait $GAME_PID
echo ">>> Game Bot exited. Stopping."
kill $ADMIN_PID 2>/dev/null || true
exit $?
