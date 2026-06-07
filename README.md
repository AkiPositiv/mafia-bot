# 🎴 Мафия — Telegram Bot Platform

Два Telegram-бота для онлайн-игры в Мафию: **Game Bot** (для игровых чатов) и **Admin Bot** (панель управления).

## 🚀 Быстрый старт

### 1. Скопируй `.env.example` → `.env`
```bash
cp .env.example .env
```

Заполни `.env`:
```env
GAME_BOT_TOKEN=токен_game_бота
ADMIN_BOT_TOKEN=токен_admin_бота
ADMIN_IDS=твой_telegram_user_id
DATABASE_URL=postgresql+asyncpg://mafia:mafia_secret@postgres:5432/mafia_db
```

### 2. Запуск через Docker Compose (рекомендуется)
```bash
docker compose up -d
```

### 3. Локальный запуск (разработка)

#### Установка зависимостей
```bash
pip install -r requirements.txt
```

#### Запуск PostgreSQL (или используй Docker)
```bash
docker run -d --name mafia_pg \
  -e POSTGRES_USER=mafia \
  -e POSTGRES_PASSWORD=mafia_secret \
  -e POSTGRES_DB=mafia_db \
  -p 5432:5432 postgres:16-alpine
```

#### Применить миграции
```bash
# БД создаётся автоматически при старте ботов (create_tables)
# Для production — используй Alembic:
alembic upgrade head
```

#### Запуск ботов
```bash
# Game Bot
python game_bot.py

# Admin Bot (в отдельном терминале)
python admin_bot.py
```

---

## 🎮 Команды Game Bot

| Команда | Где | Описание |
|---|---|---|
| `/start [ref_ID]` | ЛС | Регистрация (с реферальной ссылкой) |
| `/profile` | ЛС | Профиль, баланс, инвентарь |
| `/shop` | ЛС | Магазин предметов и ролей |
| `/ref` | ЛС | Реферальная ссылка |
| `/convert <n>` | ЛС | Обмен алмазов на монеты |
| `/transfer <uid> <n>` | ЛС | Передать алмазы игроку |
| `/newgame` | Группа | Создать лобби |
| `/join` | Группа | Войти в лобби |
| `/startgame` | Группа | Начать игру |
| `/endgame` | Группа | Завершить игру |

---

## 🛠 Команды Admin Bot

| Команда | Описание |
|---|---|
| `/addchat <chat_id>` | Добавить чат в белый список |
| `/delchat <chat_id>` | Удалить чат из белого списка |
| `/listchats` | Список разрешённых чатов |
| `/give_diamonds <uid> <n>` | Выдать алмазы |
| `/take_diamonds <uid> <n>` | Изъять алмазы |
| `/give_coins <uid> <n>` | Выдать монеты |
| `/take_coins <uid> <n>` | Изъять монеты |
| `/ban <uid> [reason]` | Заблокировать пользователя |
| `/unban <uid>` | Разблокировать |
| `/info <uid>` | Полный профиль пользователя |
| `/broadcast <текст>` | Рассылка всем пользователям |

> Admin Bot доступен только тем, чей `user_id` указан в `ADMIN_IDS`.

---

## 💰 Экономика

| Параметр | Значение |
|---|---|
| Стартовые монеты | 50 🪙 |
| Награда за победу | 30 🪙 |
| Курс конвертации | 1 💎 = 100 🪙 |
| Щит | 20 🪙 |
| Документы | 30 🪙 |
| Серебряная пуля | 1 💎 |
| Роль (обычная) | 3 💎 |
| Роль (уникальная) | 5 💎 |

---

## 🗂 Структура проекта

```
mafia/
├── game_bot.py              # Точка входа Game Bot
├── admin_bot.py             # Точка входа Admin Bot
├── requirements.txt
├── docker-compose.yml
├── alembic.ini
├── migrations/              # Alembic миграции
└── bot/
    ├── config.py            # Настройки (pydantic-settings)
    ├── middleware.py        # Whitelist + BanCheck
    ├── database/
    │   ├── models.py        # ORM: 8 таблиц
    │   ├── engine.py        # Async SQLAlchemy engine
    │   └── crud.py          # CRUD операции
    ├── game/
    │   ├── roles.py         # 20 ролей
    │   ├── balance_matrix.py # Матрица 4-30 игроков
    │   ├── engine.py        # Игровой движок (state machine)
    │   ├── notify.py        # Engine events → Telegram
    │   └── registry.py     # Реестр активных игр
    ├── handlers/
    │   ├── game/            # lobby, night, vote, shop
    │   ├── admin/           # Команды Admin Bot
    │   └── common/          # profile, start, ref
    ├── keyboards/
    │   └── game_kb.py       # Все inline-клавиатуры
    └── utils/
        ├── economy.py       # Регистрация, награды, конвертация
        └── referral.py      # 7-дневная реферальная прогрессия
```
