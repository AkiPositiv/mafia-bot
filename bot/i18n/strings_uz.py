"""O'zbek tilidagi satrlar — Mafia boti."""

STRINGS: dict[str, str] = {
    # ═══════ Rollar — label / description / goal ═══════
    "role_civilian_label": "Oddiy fuqaro",
    "role_civilian_desc": "Sizda maxsus tungi qobiliyatlar yo'q. Sizning qurolingiz — mantiq va kunduzgi ovoz berish.",
    "role_civilian_goal": "Barcha mafiya va neytral qotillarni aniqlash va jazolash.",

    "role_commissioner_label": "Komissar",
    "role_commissioner_desc": "Kechasi siz o'yinchini tekshirishingiz (uning tomonini bilish) yoki o'q uzishingiz mumkin.",
    "role_commissioner_goal": "Shaharni o'z tekshiruvlari va aniq o'qlari bilan himoya qilish.",

    "role_sergeant_label": "Serjant",
    "role_sergeant_desc": "Siz Komissarning tekshiruv natijalarini ko'rasiz. Agar u halok bo'lsa, siz uning o'rnini egallaysiz.",
    "role_sergeant_goal": "Komissarga yordam berish va u halok bo'lsa, ishini davom ettirish.",

    "role_doctor_label": "Shifokor",
    "role_doctor_desc": "Kechasi siz bitta o'yinchini hujumdan saqlab qolishingiz mumkin. O'zingizni har ikkinchi kecha davolashingiz mumkin.",
    "role_doctor_goal": "Muhim tinch o'yinchilarning hayotini saqlab qolish.",

    "role_prostitute_label": "Fohisha",
    "role_prostitute_desc": "Siz kechasi boradigan o'yinchini tanlaysiz. U maftun bo'ladi va o'z harakatini bajara olmaydi.",
    "role_prostitute_goal": "Mafiya va qotillarga iflos ishlarini bajarishiga to'sqinlik qilish.",

    "role_mayor_label": "Mer",
    "role_mayor_desc": "Kunduzgi ovoz berishda sizning ovozingiz ikkitaga teng. Hamma sizni Mer ekanligingizni biladi.",
    "role_mayor_goal": "Shaharni boshqarish va ovoz berishda muhim qarorlar qabul qilish.",

    "role_journalist_label": "Jurnalist",
    "role_journalist_desc": "Siz ikkita o'yinchini tanlaysiz va ularning bir jamoada yoki turli jamoalarda ekanligini bilib olasiz.",
    "role_journalist_goal": "O'yinchilar orasidagi aloqalarni fosh qilish va mafiyani topish.",

    "role_witness_label": "Guvoh",
    "role_witness_desc": "Siz o'yinchining eshigini kuzatasiz. Agar u bu kecha o'ldirilsa, siz qotilning yuzini ko'rasiz.",
    "role_witness_goal": "Jinoyatchilarga qarshi inkor qilib bo'lmaydigan dalillar topish.",

    "role_armorer_label": "Zirhchi",
    "role_armorer_desc": "Har 3 kechada siz o'yinchiga bronjilet berishingiz mumkin (o'zingizga — faqat 1 marta). Jilet bitta o'qdan saqlaydi (Ninja bundan mustasno).",
    "role_armorer_goal": "Shaharni himoya bilan ta'minlash.",

    "role_necromancer_label": "Nekromant",
    "role_necromancer_desc": "Har 3 kechada siz o'yinchini tiriltira olasiz. U o'yinga avval halok bo'lgan tasodifiy rol bilan qaytadi.",
    "role_necromancer_goal": "Halok bo'lgan ittifoqchilarni safga qaytarish.",

    "role_mafia_label": "Mafiya",
    "role_mafia_desc": "Siz jinoyat sindikatining a'zosisiz. Kechasi siz jamoa bilan birga qurbonni tanlash uchun ovoz berasiz.",
    "role_mafia_goal": "Barcha tinch fuqarolar va neytralarni yo'q qilish.",

    "role_don_label": "Mafiya Doni",
    "role_don_desc": "Qurbonni tanlashda sizning ovozingiz hal qiluvchi. Shuningdek, siz o'yinchilar orasidan Komissarni qidirasiz.",
    "role_don_goal": "Mafiyani boshqarish va asosiy dushman — Komissarni topish.",

    "role_lawyer_label": "Advokat",
    "role_lawyer_desc": "Siz o'yinchini tanlaysiz va unga kunduzgi suddan himoya berasiz (ertaga uni jazolash mumkin emas).",
    "role_lawyer_goal": "Sheriklar ni dordan himoya qilish.",

    "role_ninja_label": "Ninja",
    "role_ninja_desc": "Sizning hujumingiz yashirin va halokatli: u Shifokorniing davolashini va bronjiletni e'tiborsiz qoldiradi.",
    "role_ninja_goal": "Shaharning eng himoyalangan nishonlarini yo'q qilish.",

    "role_werewolf_label": "Bo'ri",
    "role_werewolf_desc": "Mafiya tirik ekan, siz tinch fuqarodek ko'rinasiz. Barcha mafiya halok bo'lganda, siz uyg'onasiz va o'ldira boshlaysiz.",
    "role_werewolf_goal": "O'z soatini kutish va shaharning yangi dahshati bo'lish.",

    "role_maniac_label": "Manyak",
    "role_maniac_desc": "Siz yolg'iz harakat qilasiz. Har kecha o'ldirish uchun qurbonni tanlaysiz.",
    "role_maniac_goal": "Bu shaharda oxirgi tirik qolgan bo'lish.",

    "role_jester_label": "Masxaraboz",
    "role_jester_desc": "Siz hammaga shubhali ko'rinasiz. Sizning vazifangiz — shaharni o'zingizni jazolashga undash.",
    "role_jester_goal": "Kunduzgi ovoz berishda osilib jazolash.",

    "role_terrorist_label": "Terrorist",
    "role_terrorist_desc": "Agar sizni kechasi o'ldirishsa, siz qotilni o'zingiz bilan olib ketasiz. Agar kunduz jazoq olsangiz — yutqazdingiz.",
    "role_terrorist_goal": "Tungi mehmoningizni yo'q qilish.",

    "role_poisoner_label": "Zaharchi",
    "role_poisoner_desc": "Sizning zahringiz darhol ta'sir qilmaydi. Tanlangan o'yinchi faqat keyingi kunning oxirida o'ladi.",
    "role_poisoner_goal": "O'lim va tartibsizlik urug'ini sepish.",

    "role_bartender_label": "Barmen",
    "role_bartender_desc": "Har 2 kechada siz o'yinchini maxsus ichimlik bilan siylaysiz. Siz uning qobiliyatini o'g'irlaysiz va qurbonni bloklaysiz.",
    "role_bartender_goal": "Boshqalarning iste'dodlarini o'z foydasiga ishlatish.",

    # ═══════ Jamoalar (Team) ═══════
    "team_town": "🕊 Tinch aholi",
    "team_mafia": "🔪 Mafiya",
    "team_neutral": "⚡ Neytral",

    # ═══════ game_started ═══════
    "game_started": "🎮 <b>O'yin boshlandi!</b>\n\n👥 O'yinchilar: <b>{count}</b>\nRollar shaxsiy xabarlarga yuborildi.\n\n🌙 Birinchi tun boshlanmoqda...",
    "your_role": "🎭 <b>Sizning rolingiz: {emoji} {label}</b>\n\n📜 <b>Tavsif:</b>\n<i>{description}</i>\n\n🎯 <b>Maqsad:</b>\n{goal}\n\n👥 Jamoa: <b>{team}</b>",
    "your_team": "\n\n🤝 <b>Sizning jamoangiz:</b>\n{teammates}",

    # ═══════ night_started ═══════
    "night_started": "🌙 <b>Tun #{day}</b>\n\n{players}\n\n{role_breakdown}\n\n⏱ Harakatlar uchun: {duration} sek.\n\n<i>Bot orqali shaxsiy xabarlarda harakat qiling.</i>",

    # ═══════ night_ended ═══════
    "night_ended_safe": "🌅 <b>Tun #{day} tugadi.</b>\nHamma tirik — bu kecha hech kim o'lmadi!",
    "night_ended_header": "🌅 <b>Tun #{day} tugadi.</b>\n\n",
    "death_line": "💀 <b>{name}</b> — {emoji} <i>{label}</i>\n    ⚔️ Bu kecha o'ldirdi: {killers}",
    "death_line_no_reason": "💀 <b>{name}</b> — {emoji} <i>{label}</i>",
    "afk_kicked": "\n😴 {roles} uxlashni tanladi va o'yindan chiqarildi!",
    "vest_saved_chat": "\n🛡 Qalqon bu kecha kimningdir hayotini saqlab qoldi!",
    "vest_saved_dm": "🛡 <b>Qalqon bu kecha hayotingizni saqlab qoldi!</b>\nQalqon yo'q qilindi.",

    # Kill reasons
    "kill_mafia": "Mafiya 🔪",
    "kill_maniac": "Manyak 🔨",
    "kill_commissioner": "Komissar 🔫",
    "kill_ninja": "Ninja 🥷",
    "kill_terrorist_explosion": "Terrorist 💥",
    "kill_werewolf": "Bo'ri 🐺",

    # ═══════ day_started ═══════
    "day_started": "☀️ <b>Kun #{day}</b> — muhokama!\n",
    "day_alive_count": "👥 <b>Tirik: {count}</b>\n\n",
    "day_poison_header": "\n\n☠️ <b>Zahar ta'siri:</b>\n",
    "day_discuss_time": "\n\n💬 Muhokama vaqti: {duration} sek.",
    "last_word_dm": "💀 Siz halok bo'ldingiz, lekin sizda 60 soniya <b>so'nggi so'z</b> uchun vaqt bor. Menga javob yozing.",

    # ═══════ vote ═══════
    "vote_started": "🗳 <b>Ovoz berish!</b> ({duration} sek.)\nTanlash <b>bot bilan shaxsiy xabarlarda</b> amalga oshiriladi.\nKim kimga ovoz berganini shu yerda ko'rasiz.",
    "vote_dm": "🗳 <b>Ovoz berish!</b> Kimni jazolashni tanlang:",
    "vote_cast": "🗳 {voter} {target} ga qarshi ovoz berdi",
    "vote_skip": "🗳 {voter} ovoz berishdan voz kechdi",

    # ═══════ trial ═══════
    "trial_header": "⚖️ <b>SUD BOSHLANADI!</b>\nKo'pchilik <b>{name}</b> ga qarshi ovoz berdi.\n\nSizda 15 soniya bor, uning taqdirini hal qiling.\nSiz haqiqatan ham bu o'yinchini osishni xohlaysizmi?",
    "trial_vote_prompt": "⚖️ <b>Ovoz bering!</b> 👍 osish / 👎 kechirim",
    "trial_no_victim": "⚖️ <b>Tenglik!</b> Hech kim jazolamnadi.",
    "trial_suspect": "⚖️ <b>{name}</b> ga shubha tushdi. Sud boshlanadi!",
    "trial_acquitted": "⚖️ <b>Oqlangan!</b>\n👍 Tarafdor: {likes} | 👎 Qarshi: {dislikes}\nFuqarolar o'yinchini kechirdi.",
    "trial_executed": "⚖️ <b>Jazolangan!</b>\n👍 Tarafdor: {likes} | 👎 Qarshi: {dislikes}\n💀 <b>{name}</b> {emoji} <i>{label}</i> edi",
    "trial_jester_win": "🃏 <b>{name}</b> osildi! (Tarafdor: {likes} | Qarshi: {dislikes})\nLekin bu <b>Masxaraboz</b> edi! U g'alaba qozondi! 🎉",

    # ═══════ game_finished ═══════
    "game_over_town": "🏆 <b>TINCH AHOLI G'ALABASI!</b>\nShahar erkin uyg'ondi. Barcha mafiya yo'q qilindi!",
    "game_over_mafia": "🏆 <b>MAFIYA G'ALABASI!</b>\nQorong'ulik shaharni qamrab oldi. Mafiya hokimiyatni egalladi!",
    "game_over_maniac": "🏆 <b>MANYAK G'ALABASI!</b>\nShahar bo'shab qoldi. Manyak oxirgi bo'lib qoldi...",
    "game_over_nobody": "🏳️ <b>DURRANG!</b>\nBu jangda g'olib yo'q.",
    "game_over_players_header": "\n\n👥 <b>Barcha o'yinchilar:</b>\n",
    "game_over_player_alive": "✅ {name} — {emoji} {label}",
    "game_over_player_dead": "💀 {name} — {emoji} {label}",
    "game_over_duration": "\n\n⏱ O'yin {minutes} daq {seconds} sek davom etdi.",

    # ═══════ Sergeant / Werewolf ═══════
    "sergeant_promoted_chat": "🪖 Serjant Komissar o'rnini egalladi! (ID: {uid})\nRol shaxsiy xabarga yuborildi.",
    "sergeant_promoted_dm": "🔫 Siz <b>Komissar</b> bo'ldingiz! Komissar halok bo'ldi va siz uning o'rnini egallaysiz.",
    "werewolf_activated_chat": "🐺 <b>Shaharda bo'ri uvladi!</b>\nBarcha mafiya yo'q qilindi, lekin xavf o'tmadi...",
    "werewolf_activated_dm": "🐺 Siz <b>faollashdingiz</b>! Endi siz har kecha o'ldirasiz.",

    # ═══════ lobby ═══════
    "lobby_expired": "❌ Ro'yxatga olish tugadi. O'yinchilar yetarli emas ({count}/{min}).",
    "no_players_in_chat": "🕵️ Bu chatda hali hech kim o'ynamagan.",
    "nobody_in_chat": "🕵️ Hozir chatda o'yinchilardan hech kim yo'q.",
    "call_header": "🔔 <b>Umumiy yig'ilish!</b>\n\n",

    # ═══════ Night DM texts ═══════
    "night_dm_doctor": "💊 <b>Shifokor</b>, bu kecha kimni saqlashni tanlang:",
    "night_dm_doctor_healed_self": "⚠️ Siz allaqachon o'zingizni davolagansiz. Boshqa o'yinchini tanlang:",
    "night_dm_commissioner": "🔫 <b>Komissar</b>, harakatni tanlang:",
    "night_dm_commissioner_check": "🔍 <b>Tekshirish</b> uchun tanlang:",
    "night_dm_commissioner_shoot": "🔫 Kimga <b>o'q uzish</b>ni tanlang:",
    "night_dm_commissioner_result_mafia": "🔍 Tekshiruv natijasi: <b>{name}</b> — ❌ <b>Mafiya!</b>",
    "night_dm_commissioner_result_town": "🔍 Tekshiruv natijasi: <b>{name}</b> — ✅ <b>Tinch aholi</b>",
    "night_dm_prostitute": "💋 <b>Fohisha</b>, bu kecha kimni maftun qilishni tanlang:",
    "night_dm_mafia_header": "🔪 <b>Mafiya</b>, qurbonni tanlang.\nSizning jamoangiz:\n{team}",
    "night_dm_mafia_vote": "🔪 <b>Mafiya</b>, qurbon uchun ovoz bering:",
    "night_dm_ninja": "🥷 <b>Ninja</b>, o'ldirish uchun qurbonni tanlang:",
    "night_dm_maniac": "🔨 <b>Manyak</b>, qurbonni tanlang:",
    "night_dm_poisoner": "☠️ <b>Zaharchi</b>, kimni zaharlab qilishni tanlang:",
    "night_dm_lawyer": "⚖️ <b>Advokat</b>, kimga suddan imtiyoz berishni tanlang:",
    "night_dm_witness": "👀 <b>Guvoh</b>, kimning eshigini kuzatishni tanlang:",
    "night_dm_journalist": "📰 <b>Jurnalist</b>, solishtirish uchun <b>birinchi</b> o'yinchini tanlang:",
    "night_dm_journalist_p2": "📰 Endi <b>ikkinchi</b> o'yinchini tanlang:",
    "night_dm_journalist_result_same": "📰 Natija: <b>{name1}</b> va <b>{name2}</b> — <b>bir jamoa</b>.",
    "night_dm_journalist_result_diff": "📰 Natija: <b>{name1}</b> va <b>{name2}</b> — <b>turli jamoalar</b>.",
    "night_dm_armorer": "🛡️ <b>Zirhchi</b>, kimga bronjilet berishni tanlang:",
    "night_dm_armorer_cooldown": "🛡️ Kutish: yana {n} kecha keyingi jiletgacha.",
    "night_dm_necromancer": "💀 <b>Nekromant</b>, kimni tiriltirishni tanlang:",
    "night_dm_necromancer_cooldown": "💀 Kutish: yana {n} kecha keyingi tiriltririshgacha.",
    "night_dm_bartender": "🍺 <b>Barmen</b>, kimga ichimlik quying:",
    "night_dm_bartender_cooldown": "🍺 Kutish: yana {n} kecha keyingi ichimlikgacha.",
    "night_dm_werewolf": "🐺 <b>Bo'ri</b>, qurbonni tanlang:",

    # Night action confirmation
    "action_confirmed": "✅ Qabul qilindi! Harakatingiz yozildi.",
    "action_skip": "⏭ Siz navbatni o'tkazib yubordingiz.",

    # action_submitted (chat flavor texts)
    "action_flavor_commissioner_shoot": "🔫 Komissar to'pponchani to'ldirdi",
    "action_flavor_commissioner_check": "🔍 Komissar tun jimjitligida yovuzlarni qidirmoqda.",
    "action_flavor_mafia": "🔪 Mafiya keyingi nishonni tanladi...",
    "action_flavor_don": "🎩 Mafiya Doni yo'q qilish buyrug'ini berdi.",
    "action_flavor_doctor": "💊 Shifokor bu kecha hayot saqlab qolish uchun jo'nadi.",
    "action_flavor_prostitute": "💋 Fohisha navbatdagi mijozni maftun etishga ketdi.",
    "action_flavor_maniac": "🔨 Manyak tungi ovga chiqdi...",
    "action_flavor_ninja": "🥷 Ninja soyasi tor ko'chalarda sirg'aldi.",
    "action_flavor_poisoner": "☠️ Zaharchi halokatli dozani tayyorlamoqda.",
    "action_flavor_bartender": "🍺 Barmen yangi qurbonni o'z muassasasiga jalb qilmoqda.",
    "action_flavor_lawyer": "⚖️ Advokat o'z manfaatlarini himoya qilish uchun hujjatlar tayyorlamoqda.",
    "action_flavor_witness": "👀 Guvoh pana bo'lib, voqealarni kuzatmoqda.",
    "action_flavor_armorer": "🛡️ Zirhchi yangi himoya yasmoqda.",
    "action_flavor_necromancer": "💀 Tor ko'chalarda sovuq hid kelmoqda — Nekromant sehr qilmoqda.",
    "action_flavor_default": "✨ Kimdir tungi harakat qildi...",

    # ═══════ last word ═══════
    "last_word_received": "📢 <b>{name} ning so'nggi so'zi</b>:\n<i>{text}</i>",

    # ═══════ Keyboard buttons ═══════
    "btn_join": "➕ Qo'shilish",
    "btn_skip": "⏭ O'tkazish",
    "btn_check": "🔍 Tekshirish",
    "btn_shoot": "🔫 O'q uzish",
    "btn_abstain": "🚫 Voz kechish",
    "btn_hang": "👍 Osish ({n})",
    "btn_pardon": "👎 Kechirish ({n})",
    "btn_go_to_chat": "💬 Chatga o'tish",
    "btn_back_profile": "◀ Profilga",
    "btn_shield": "🛡 Qalqon — 150 tanga",
    "btn_docs": "📄 Hujjatlar — 200 tanga",
    "btn_silver_bullet": "🥈 Kumush o'q — 1 💎",
    "btn_buy_role": "🎭 Rol sotib olish — 1-3 💎",
    "btn_confirm": "✅ Tasdiqlash",
    "btn_cancel": "❌ Bekor qilish",
    "btn_back": "◀ Orqaga",
    "btn_exchange": "🔃 Almashtirish 💎 → 🪙",
    "btn_buy_diamonds": "💎 Olmos sotib olish",

    # ═══════ /lang ═══════
    "lang_prompt": "🌐 <b>Выберите язык / Tilni tanlang:</b>",
    "lang_set": "✅ Til o'rnatildi: <b>O'zbek</b> 🇺🇿",

    # ═══════ Living roles format ═══════
    "living_header": "👥 <b>Tirik o'yinchilar: {count}</b>\n",
    "living_mafia": "🔪 <b>Mafiya — {count}</b>",
    "living_town": "👨‍👩‍👧‍👦 <b>Tinch aholi — {count}</b>",
    "living_neutral": "⚡ <b>Neytralar — {count}</b>",

    # ═══════ Moderation ═══════
    "mod_muted": "🔇 {admin} {target} ni {minutes} daq mutelab qo'ydi.\nSabab: {reason}",
    "mod_unmuted": "✅ {admin} {target} ni mutedan chiqardi.",
    "mod_warned": "⚠️ {admin} {target} ga ogohlantirish berdi ({count}/3).\nSabab: {reason}",
    "mod_warn_ban": "🚫 {target} 3 ta ogohlantirish oldi va banlandi!",
    "mod_unwarned": "✅ {admin} {target} dan ogohlantirishni olib tashladi ({count}/3).",
    "mod_banned": "🚫 {admin} {target} ni banladi.\nSabab: {reason}",
    "mod_unbanned": "✅ {admin} {target} ni bandan chiqardi.",
    "mod_not_admin": "❌ Siz administrator emassiz.",
    "mod_reply_required": "↩️ Foydalanuvchi xabariga javob bering.",
}
