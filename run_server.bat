@echo off
setlocal

:: Переходим в папку с проектом
cd /d "%~dp0"

echo ======================================================
echo   🎭 MAFIA BOT SERVER - ЗАПУСК ЛОКАЛЬНОГО СЕРВЕРА
echo ======================================================
echo.

:: 1. Установка/обновление зависимостей
echo [1/4] Проверка и установка зависимостей...
pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo [!] Ошибка при установке pip-зависимостей.
    pause
    exit /b %ERRORLEVEL%
)

:: 2. Проверка и запуск PostgreSQL через Docker
echo [2/4] Проверка Docker и запуск базы данных (PostgreSQL)...
docker ps > nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [!] ОШИБКА: Docker не запущен или не отвечает.
    echo [!] Пожалуйста, запустите Docker Desktop и убедитесь, что он готов к работе.
    pause
    exit /b 1
)
docker compose up -d postgres
if %ERRORLEVEL% neq 0 (
    echo [!] Ошибка при выполнении docker compose up. Убедитесь, что Docker Desktop запущен.
    pause
    exit /b %ERRORLEVEL%
)

:: Ждём готовности PostgreSQL (до 30 секунд)
echo Ожидание готовности PostgreSQL...
set /a attempts=0
:wait_loop
docker exec mafia-postgres-1 pg_isready -U mafia -d mafia_db > nul 2>&1
if %ERRORLEVEL% equ 0 goto db_ready
set /a attempts+=1
if %attempts% geq 12 (
    echo [!] PostgreSQL не ответил за 60 секунд. Продолжаем с ошибкой...
    goto db_ready
)
timeout /t 5 /nobreak > nul
goto wait_loop

:db_ready
echo PostgreSQL готов!

:: 3. Применение миграций базы данных
echo [3/4] Применение миграций базы данных...
python -m alembic upgrade head
if %ERRORLEVEL% neq 0 (
    echo [!] Ошибка при выполнении миграций.
)


:: 4. Запуск ботов в отдельных окнах
echo [4/4] Запуск ботов...

:: Запуск Game Bot
echo Запуск Game Bot в новом окне...
start "Mafia Game Bot" cmd /k "python game_bot.py"

:: Запуск Admin Bot
echo Запуск Admin Bot в новом окне...
start "Mafia Admin Bot" cmd /k "python admin_bot.py"

echo.
echo ✅ СЕРВЕР ЗАПУЩЕН!
echo ------------------------------------------------------
echo Текущая конфигурация:
echo Game Token:  8411682585:***FrSQ
echo Admin Token: 8555363039:***WGlk
echo Admin ID:    1075491040
echo ------------------------------------------------------
echo.
echo Это окно можно закрыть. Боты продолжат работу в своих окнах.
echo Чтобы остановить базу данных, используйте: docker compose down
echo.
pause
