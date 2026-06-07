"""Русские строки для бота Мафия."""

STRINGS: dict[str, str] = {
    # ═══════ Роли — label / description / goal ═══════
    "role_civilian_label": "Мирный житель",
    "role_civilian_desc": "У вас нет особых ночных способностей. Ваше оружие — логика и дневное голосование.",
    "role_civilian_goal": "Вычислить и казнить всю мафию и нейтральных убийц.",

    "role_commissioner_label": "Комиссар",
    "role_commissioner_desc": "Ночью вы можете проверить игрока (узнать его сторону) или выстрелить на поражение.",
    "role_commissioner_goal": "Защищать город, используя свои проверки и точные выстрелы.",

    "role_sergeant_label": "Сержант",
    "role_sergeant_desc": "Вы видите результаты проверок Комиссара. В случае его гибели вы займёте его пост.",
    "role_sergeant_goal": "Помогать Комиссару и продолжить его дело, если он падет.",

    "role_doctor_label": "Доктор",
    "role_doctor_desc": "Ночью вы можете спасти одного игрока от нападения. Себя лечить можно через раз.",
    "role_doctor_goal": "Сохранить жизнь ключевым мирным игрокам.",

    "role_prostitute_label": "Проститутка",
    "role_prostitute_desc": "Вы выбираете игрока, к которому пойдете ночью. Он будет очарован и не сможет совершить свой ход.",
    "role_prostitute_goal": "Мешать мафии и убийцам выполнять их грязную работу.",

    "role_mayor_label": "Мэр",
    "role_mayor_desc": "Ваш голос на дневном голосовании считается за два. Все знают, что вы Мэр.",
    "role_mayor_goal": "Вести город за собой и принимать ключевые решения на голосовании.",

    "role_journalist_label": "Журналист",
    "role_journalist_desc": "Вы выбираете двух игроков и узнаёте, играют ли они за одну команду или за разные.",
    "role_journalist_goal": "Разоблачать связи между игроками и находить мафию.",

    "role_witness_label": "Свидетель",
    "role_witness_desc": "Вы следите за дверью игрока. Если его убьют этой ночью, вы увидите лицо убийцы.",
    "role_witness_goal": "Найти неопровержимые улики против преступников.",

    "role_armorer_label": "Броненосец",
    "role_armorer_desc": "Раз в 3 ночи вы можете выдать бронежилет игроку (себе — только 1 раз). Жилет спасает от одного выстрела (кроме Ниндзя).",
    "role_armorer_goal": "Снабжать город защитой.",

    "role_necromancer_label": "Некромант",
    "role_necromancer_desc": "Раз в 3 ночи вы можете воскресить игрока. Он вернется в игру со случайной ранее погибшей ролью.",
    "role_necromancer_goal": "Возвращать павших союзников в строй.",

    "role_mafia_label": "Мафия",
    "role_mafia_desc": "Вы — член преступного синдиката. Ночью вы голосуете вместе с командой за выбор жертвы.",
    "role_mafia_goal": "Устранить всех мирных жителей и нейтралов, пока вас не стало больше.",

    "role_don_label": "Дон Мафии",
    "role_don_desc": "Ваш голос при выборе жертвы решающий. Также вы ищете Комиссара среди игроков.",
    "role_don_goal": "Возглавить мафию и найти главного врага — Комиссара.",

    "role_lawyer_label": "Адвокат",
    "role_lawyer_desc": "Вы выбираете игрока, которому дадите защиту от дневного правосудия (его нельзя будет казнить завтра).",
    "role_lawyer_goal": "Защищать сообщников от виселицы.",

    "role_ninja_label": "Ниндзя",
    "role_ninja_desc": "Ваша атака скрытна и смертоносна: она игнорирует лечение Доктора и бронежилет.",
    "role_ninja_goal": "Уничтожать самые защищенные цели города.",

    "role_werewolf_label": "Оборотень",
    "role_werewolf_desc": "Пока жива мафия, вы выглядите как мирный житель. Когда вся мафия погибнет, вы пробуждаетесь и начинаете убивать.",
    "role_werewolf_goal": "Дождаться своего часа и стать новым кошмаром города.",

    "role_maniac_label": "Маньяк",
    "role_maniac_desc": "Вы действуете в одиночку. Каждую ночь вы выбираете жертву для убийства.",
    "role_maniac_goal": "Остаться последним выжившим в этом городе.",

    "role_jester_label": "Шут",
    "role_jester_desc": "Вы кажетесь всем подозрительным. Ваша задача — спровоцировать город на свою казнь.",
    "role_jester_goal": "Быть повешенным на дневном голосовании.",

    "role_terrorist_label": "Террорист",
    "role_terrorist_desc": "Если вас убьют ночью, вы заберете убийцу с собой. Если вас казнят днем — вы проиграли.",
    "role_terrorist_goal": "Уничтожить своего ночного гостя.",

    "role_poisoner_label": "Отравитель",
    "role_poisoner_desc": "Ваш яд действует не сразу. Выбранный игрок умрет только в конце следующего дня (после обсуждения).",
    "role_poisoner_goal": "Сеять смерть и хаос, наблюдая за мучениями жертв.",

    "role_bartender_label": "Бармен",
    "role_bartender_desc": "Раз в 2 ночи вы угощаете игрока особым напитком. Вы крадете его способность и применяете её сами, блокируя жертву.",
    "role_bartender_goal": "Использовать чужие таланты для своей выгоды.",

    # ═══════ Команды (Team) ═══════
    "team_town": "🕊 Мирные",
    "team_mafia": "🔪 Мафия",
    "team_neutral": "⚡ Нейтрал",

    # ═══════ game_started ═══════
    "game_started": "🎮 <b>Игра началась!</b>\n\n👥 Игроков: <b>{count}</b>\nРоли отправлены в ЛС.\n\n🌙 Впереди — первая ночь...",
    "your_role": "🎭 <b>Ваша роль: {emoji} {label}</b>\n\n📜 <b>Описание:</b>\n<i>{description}</i>\n\n🎯 <b>Цель:</b>\n{goal}\n\n👥 Команда: <b>{team}</b>",
    "your_team": "\n\n🤝 <b>Ваша команда:</b>\n{teammates}",

    # ═══════ night_started ═══════
    "night_started": "🌙 <b>Ночь #{day}</b>\n\n{players}\n\n{role_breakdown}\n\n⏱ На ходы: {duration} сек.\n\n<i>Действуйте через ЛС бота.</i>",

    # ═══════ night_ended ═══════
    "night_ended_safe": "🌅 <b>Ночь #{day} закончилась.</b>\nВсе живы — никто не умер этой ночью!",
    "night_ended_header": "🌅 <b>Ночь #{day} закончилась.</b>\n\n",
    "death_line": "💀 <b>{name}</b> — {emoji} <i>{label}</i>\n    ⚔️ Этой ночью убили: {killers}",
    "death_line_no_reason": "💀 <b>{name}</b> — {emoji} <i>{label}</i>",
    "afk_kicked": "\n😴 {roles} выбрал(а) сон и был(а) убран(а) из игры!",
    "vest_saved_chat": "\n🛡 Щит спас чью-то жизнь этой ночью!",
    "vest_saved_dm": "🛡 <b>Ваш щит спас вам жизнь этой ночью!</b>\nЩит уничтожен.",

    # Kill reasons
    "kill_mafia": "Мафия 🔪",
    "kill_maniac": "Маньяк 🔨",
    "kill_commissioner": "Комиссар 🔫",
    "kill_ninja": "Ниндзя 🥷",
    "kill_terrorist_explosion": "Террорист 💥",
    "kill_werewolf": "Оборотень 🐺",

    # ═══════ day_started ═══════
    "day_started": "☀️ <b>День #{day}</b> — обсуждение!\n",
    "day_alive_count": "👥 <b>Живых: {count}</b>\n\n",
    "day_poison_header": "\n\n☠️ <b>Действие яда:</b>\n",
    "day_discuss_time": "\n\n💬 Время обсуждения: {duration} сек.",
    "last_word_dm": "💀 Вы погибли, но у вас есть 60 секунд на <b>последнее слово</b>. Просто напишите его мне в ответ.",

    # ═══════ vote ═══════
    "vote_started": "🗳 <b>Голосование!</b> ({duration} сек.)\nВыбор происходит <b>в ЛС у бота</b>.\nКто за кого голосует — будет видно здесь.",
    "vote_dm": "🗳 <b>Голосование!</b> Выберите, кого линчевать:",
    "vote_cast": "🗳 {voter} проголосовал против {target}",
    "vote_skip": "🗳 {voter} воздержался от голосования",

    # ═══════ trial ═══════
    "trial_header": "⚖️ <b>СУД ИДЕТ!</b>\nБольшинство проголосовало против <b>{name}</b>.\n\nУ вас есть 15 секунд, чтобы решить его судьбу.\nВы реально хотите повесить данного игрока?",
    "trial_vote_prompt": "⚖️ <b>Голосуйте!</b> 👍 повесить / 👎 помиловать",
    "trial_no_victim": "⚖️ <b>Ничья!</b> Никто не казнён.",
    "trial_suspect": "⚖️ Подозрение пало на <b>{name}</b>. Начинается суд!",
    "trial_acquitted": "⚖️ <b>Оправдан!</b>\n👍 За: {likes} | 👎 Против: {dislikes}\nЖители решили помиловать игрока.",
    "trial_executed": "⚖️ <b>Казнён!</b>\n👍 За: {likes} | 👎 Против: {dislikes}\n💀 <b>{name}</b> был {emoji} <i>{label}</i>",
    "trial_jester_win": "🃏 <b>{name}</b> повешен! (За: {likes} | Против: {dislikes})\nНо это был <b>Шут</b>! Он победил! 🎉",

    # ═══════ game_finished ═══════
    "game_over_town": "🏆 <b>ПОБЕДА МИРНЫХ!</b>\nГород просыпается свободным. Вся мафия уничтожена!",
    "game_over_mafia": "🏆 <b>ПОБЕДА МАФИИ!</b>\nТьма поглотила город. Мафия захватила власть!",
    "game_over_maniac": "🏆 <b>ПОБЕДА МАНЬЯКА!</b>\nГород опустел. Маньяк остался последним...",
    "game_over_nobody": "🏳️ <b>НИЧЬЯ!</b>\nВ этой битве не оказалось победителей.",
    "game_over_players_header": "\n\n👥 <b>Все игроки:</b>\n",
    "game_over_player_alive": "✅ {name} — {emoji} {label}",
    "game_over_player_dead": "💀 {name} — {emoji} {label}",
    "game_over_duration": "\n\n⏱ Игра длилась {minutes} мин {seconds} сек.",

    # ═══════ Sergeant / Werewolf ═══════
    "sergeant_promoted_chat": "🪖 Сержант занял место Комиссара! (ID: {uid})\nРоль отправлена в личные сообщения.",
    "sergeant_promoted_dm": "🔫 Вы стали <b>Комиссаром</b>! Комиссар погиб, и вы заняли его место.",
    "werewolf_activated_chat": "🐺 <b>В городе завыл Волк!</b>\nВся мафия уничтожена, но опасность не прошла...",
    "werewolf_activated_dm": "🐺 Вы <b>активировались</b>! Теперь вы убиваете каждую ночь.",

    # ═══════ lobby ═══════
    "lobby_expired": "❌ Регистрация окончена. Недостаточно игроков ({count}/{min}).",
    "no_players_in_chat": "🕵️ В этом чате ещё никто не играл.",
    "nobody_in_chat": "🕵️ Никто из игроков сейчас не в чате.",
    "call_header": "🔔 <b>Общий сбор!</b>\n\n",

    # ═══════ Night DM texts ═══════
    "night_dm_doctor": "💊 <b>Доктор</b>, выберите, кого спасти этой ночью:",
    "night_dm_doctor_healed_self": "⚠️ Вы уже лечили себя. Выберите другого игрока:",
    "night_dm_commissioner": "🔫 <b>Комиссар</b>, выберите действие:",
    "night_dm_commissioner_check": "🔍 Выберите, кого <b>проверить</b>:",
    "night_dm_commissioner_shoot": "🔫 Выберите, в кого <b>стрелять</b>:",
    "night_dm_commissioner_result_mafia": "🔍 Результат проверки: <b>{name}</b> — ❌ <b>Мафия!</b>",
    "night_dm_commissioner_result_town": "🔍 Результат проверки: <b>{name}</b> — ✅ <b>Мирный</b>",
    "night_dm_prostitute": "💋 <b>Проститутка</b>, выберите, кого очаровать этой ночью:",
    "night_dm_mafia_header": "🔪 <b>Мафия</b>, выберите жертву.\nВаша команда:\n{team}",
    "night_dm_mafia_vote": "🔪 <b>Мафия</b>, голосуйте за жертву:",
    "night_dm_ninja": "🥷 <b>Ниндзя</b>, выберите жертву для убийства:",
    "night_dm_maniac": "🔨 <b>Маньяк</b>, выберите жертву:",
    "night_dm_poisoner": "☠️ <b>Отравитель</b>, выберите, кого отравить:",
    "night_dm_lawyer": "⚖️ <b>Адвокат</b>, выберите, кому дать иммунитет от суда:",
    "night_dm_witness": "👀 <b>Свидетель</b>, выберите, за чьей дверью наблюдать:",
    "night_dm_journalist": "📰 <b>Журналист</b>, выберите <b>первого</b> игрока для сравнения:",
    "night_dm_journalist_p2": "📰 Теперь выберите <b>второго</b> игрока:",
    "night_dm_journalist_result_same": "📰 Результат: <b>{name1}</b> и <b>{name2}</b> — <b>одна команда</b>.",
    "night_dm_journalist_result_diff": "📰 Результат: <b>{name1}</b> и <b>{name2}</b> — <b>разные команды</b>.",
    "night_dm_armorer": "🛡️ <b>Броненосец</b>, выберите, кому выдать бронежилет:",
    "night_dm_armorer_cooldown": "🛡️ Кулдаун: ещё {n} ночи до следующего жилета.",
    "night_dm_necromancer": "💀 <b>Некромант</b>, выберите, кого воскресить:",
    "night_dm_necromancer_cooldown": "💀 Кулдаун: ещё {n} ночи до следующего воскрешения.",
    "night_dm_bartender": "🍺 <b>Бармен</b>, выберите, кому подлить в напиток:",
    "night_dm_bartender_cooldown": "🍺 Кулдаун: ещё {n} ночи до следующего напитка.",
    "night_dm_werewolf": "🐺 <b>Оборотень</b>, выберите жертву:",

    # Night action confirmation
    "action_confirmed": "✅ Принято! Ваш ход записан.",
    "action_skip": "⏭ Вы пропустили ход.",

    # action_submitted (chat flavor texts)
    "action_flavor_commissioner_shoot": "🔫 Комиссар зарядил пистолет",
    "action_flavor_commissioner_check": "🔍 Комиссар ушел искать злодеев в ночной тишине.",
    "action_flavor_mafia": "🔪 Мафия выбрала следующую цель...",
    "action_flavor_don": "🎩 Дон Мафии отдал приказ о ликвидации.",
    "action_flavor_doctor": "💊 Доктор отправился спасать жизни этой ночью.",
    "action_flavor_prostitute": "💋 Проститутка пошла очаровывать очередного клиента.",
    "action_flavor_maniac": "🔨 Маньяк вышел на ночную охоту...",
    "action_flavor_ninja": "🥷 Тень Ниндзя скользнула в переулках.",
    "action_flavor_poisoner": "☠️ Отравитель готовит смертельную дозу.",
    "action_flavor_bartender": "🍺 Бармен завлекает новую жертву в свое заведение.",
    "action_flavor_lawyer": "⚖️ Адвокат готовит бумаги для защиты своих интересов.",
    "action_flavor_witness": "👀 Свидетель притаился и наблюдает за происходящим.",
    "action_flavor_armorer": "🛡️ Броненосец кует новую защиту.",
    "action_flavor_necromancer": "💀 В переулках пахнет холодом — Некромант творит заклятие.",
    "action_flavor_default": "✨ Кто-то совершил ночное действие...",

    # ═══════ last word ═══════
    "last_word_received": "📢 <b>Последнее слово {name}</b>:\n<i>{text}</i>",

    # ═══════ Keyboard buttons ═══════
    "btn_join": "➕ Присоединиться",
    "btn_skip": "⏭ Пропустить",
    "btn_check": "🔍 Проверить",
    "btn_shoot": "🔫 Выстрелить",
    "btn_abstain": "🚫 Воздержаться",
    "btn_hang": "👍 Повесить ({n})",
    "btn_pardon": "👎 Помиловать ({n})",
    "btn_go_to_chat": "💬 Перейти в чат",
    "btn_back_profile": "◀ В профиль",
    "btn_shield": "🛡 Щит — 150 монет",
    "btn_docs": "📄 Документы — 200 монет",
    "btn_silver_bullet": "🥈 Сер. пуля — 1 💎",
    "btn_buy_role": "🎭 Купить роль — 1-3 💎",
    "btn_confirm": "✅ Подтвердить",
    "btn_cancel": "❌ Отмена",
    "btn_back": "◀ Назад",
    "btn_exchange": "🔃 Обмен 💎 → 🪙",
    "btn_buy_diamonds": "💎 Купить Алмазы",

    # ═══════ /lang ═══════
    "lang_prompt": "🌐 <b>Выберите язык / Tilni tanlang:</b>",
    "lang_set": "✅ Язык установлен: <b>Русский</b> 🇷🇺",

    # ═══════ Living roles format ═══════
    "living_header": "👥 <b>Живых игроков: {count}</b>\n",
    "living_mafia": "🔪 <b>Мафия — {count}</b>",
    "living_town": "👨‍👩‍👧‍👦 <b>Мирные — {count}</b>",
    "living_neutral": "⚡ <b>Нейтралы — {count}</b>",

    # ═══════ Moderation ═══════
    "mod_muted": "🔇 {admin} замутил {target} на {minutes} мин.\nПричина: {reason}",
    "mod_unmuted": "✅ {admin} размутил {target}.",
    "mod_warned": "⚠️ {admin} выдал предупреждение {target} ({count}/3).\nПричина: {reason}",
    "mod_warn_ban": "🚫 {target} получил 3 предупреждения и забанен!",
    "mod_unwarned": "✅ {admin} снял предупреждение с {target} ({count}/3).",
    "mod_banned": "🚫 {admin} забанил {target}.\nПричина: {reason}",
    "mod_unbanned": "✅ {admin} разбанил {target}.",
    "mod_not_admin": "❌ Вы не администратор.",
    "mod_reply_required": "↩️ Ответьте на сообщение пользователя.",
}
