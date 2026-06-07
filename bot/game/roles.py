"""
Определения 20 игровых ролей: команды, ночные действия, уникальность.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Team(str, Enum):
    TOWN = "town"
    MAFIA = "mafia"
    NEUTRAL = "neutral"


class RoleName(str, Enum):
    # Светлая сторона
    CIVILIAN = "civilian"
    COMMISSIONER = "commissioner"
    SERGEANT = "sergeant"
    DOCTOR = "doctor"
    PROSTITUTE = "prostitute"
    MAYOR = "mayor"
    JOURNALIST = "journalist"
    WITNESS = "witness"
    ARMORER = "armorer"
    NECROMANCER = "necromancer"
    # Тёмная сторона
    MAFIA = "mafia"
    DON = "don"
    LAWYER = "lawyer"
    NINJA = "ninja"
    WEREWOLF = "werewolf"
    # Нейтралы
    MANIAC = "maniac"
    JESTER = "jester"
    TERRORIST = "terrorist"
    POISONER = "poisoner"
    BARTENDER = "bartender"


@dataclass(frozen=True)
class Role:
    name: RoleName
    team: Team
    emoji: str
    label: str                  # Отображаемое имя на русском
    has_night_action: bool
    is_unique: bool             # Только одна такая роль в игре
    description: str            # Описание способностей
    goal: str                   # Цель игры для этой роли

    @property
    def is_mafia_side(self) -> bool:
        return self.team == Team.MAFIA

    @property
    def is_town_side(self) -> bool:
        return self.team == Team.TOWN

    @property
    def is_killer(self) -> bool:
        """Может ли роль совершать убийство (для серебряной пули)."""
        return self.name in KILLER_ROLES


KILLER_ROLES = {
    RoleName.MAFIA,
    RoleName.DON,
    RoleName.NINJA,
    RoleName.MANIAC,
    RoleName.TERRORIST,
    RoleName.POISONER,
}

# ─────────────────── Реестр всех ролей ───────────────────────

ALL_ROLES: dict[RoleName, Role] = {
    RoleName.CIVILIAN: Role(
        name=RoleName.CIVILIAN,
        team=Team.TOWN,
        emoji="👤",
        label="Мирный житель",
        has_night_action=False,
        is_unique=False,
        description="У вас нет особых ночных способностей. Ваше оружие — логика и дневное голосование.",
        goal="Вычислить и казнить всю мафию и нейтральных убийц.",
    ),
    RoleName.COMMISSIONER: Role(
        name=RoleName.COMMISSIONER,
        team=Team.TOWN,
        emoji="🔫",
        label="Комиссар",
        has_night_action=True,
        is_unique=True,
        description="Ночью вы можете проверить игрока (узнать его сторону) или выстрелить на поражение.",
        goal="Защищать город, используя свои проверки и точные выстрелы.",
    ),
    RoleName.SERGEANT: Role(
        name=RoleName.SERGEANT,
        team=Team.TOWN,
        emoji="🪖",
        label="Сержант",
        has_night_action=False,
        is_unique=False,
        description="Вы видите результаты проверок Комиссара. В случае его гибели вы займёте его пост.",
        goal="Помогать Комиссару и продолжить его дело, если он падет.",
    ),
    RoleName.DOCTOR: Role(
        name=RoleName.DOCTOR,
        team=Team.TOWN,
        emoji="💊",
        label="Доктор",
        has_night_action=True,
        is_unique=True,
        description="Ночью вы можете спасти одного игрока от нападения. Себя лечить можно через раз.",
        goal="Сохранить жизнь ключевым мирным игрокам.",
    ),
    RoleName.PROSTITUTE: Role(
        name=RoleName.PROSTITUTE,
        team=Team.TOWN,
        emoji="💋",
        label="Проститутка",
        has_night_action=True,
        is_unique=True,
        description="Вы выбираете игрока, к которому пойдете ночью. Он будет очарован и не сможет совершить свой ход.",
        goal="Мешать мафии и убийцам выполнять их грязную работу.",
    ),
    RoleName.MAYOR: Role(
        name=RoleName.MAYOR,
        team=Team.TOWN,
        emoji="🏛️",
        label="Мэр",
        has_night_action=False,
        is_unique=True,
        description="Ваш голос на дневном голосовании считается за два. Все знают, что вы Мэр.",
        goal="Вести город за собой и принимать ключевые решения на голосовании.",
    ),
    RoleName.JOURNALIST: Role(
        name=RoleName.JOURNALIST,
        team=Team.TOWN,
        emoji="📰",
        label="Журналист",
        has_night_action=True,
        is_unique=True,
        description="Вы выбираете двух игроков и узнаёте, играют ли они за одну команду или за разные.",
        goal="Разоблачать связи между игроками и находить мафию.",
    ),
    RoleName.WITNESS: Role(
        name=RoleName.WITNESS,
        team=Team.TOWN,
        emoji="👀",
        label="Свидетель",
        has_night_action=True,
        is_unique=True,
        description="Вы следите за дверью игрока. Если его убьют этой ночью, вы увидите лицо убийцы.",
        goal="Найти неопровержимые улики против преступников.",
    ),
    RoleName.ARMORER: Role(
        name=RoleName.ARMORER,
        team=Team.TOWN,
        emoji="🛡️",
        label="Броненосец",
        has_night_action=True,
        is_unique=True,
        description="Раз в 3 ночи вы можете выдать бронежилет игроку (себе — только 1 раз). Жилет спасает от одного выстрела (кроме Ниндзя).",
        goal="Снабжать город защитой.",
    ),
    RoleName.NECROMANCER: Role(
        name=RoleName.NECROMANCER,
        team=Team.TOWN,
        emoji="💀",
        label="Некромант",
        has_night_action=True,
        is_unique=True,
        description="Раз в 3 ночи вы можете воскресить игрока. Он вернется в игру со случайной ранее погибшей ролью.",
        goal="Возвращать павших союзников в строй.",
    ),
    RoleName.MAFIA: Role(
        name=RoleName.MAFIA,
        team=Team.MAFIA,
        emoji="🔪",
        label="Мафия",
        has_night_action=True,
        is_unique=False,
        description="Вы — член преступного синдиката. Ночью вы голосуете вместе с командой за выбор жертвы.",
        goal="Устранить всех мирных жителей и нейтралов, пока вас не стало больше.",
    ),
    RoleName.DON: Role(
        name=RoleName.DON,
        team=Team.MAFIA,
        emoji="🎩",
        label="Дон Мафии",
        has_night_action=True,
        is_unique=True,
        description="Ваш голос при выборе жертвы решающий. Также вы ищете Комиссара среди игроков.",
        goal="Возглавить мафию и найти главного врага — Комиссара.",
    ),
    RoleName.LAWYER: Role(
        name=RoleName.LAWYER,
        team=Team.MAFIA,
        emoji="⚖️",
        label="Адвокат",
        has_night_action=True,
        is_unique=True,
        description="Вы выбираете игрока, которому дадите защиту от дневного правосудия (его нельзя будет казнить завтра).",
        goal="Защищать сообщников от виселицы.",
    ),
    RoleName.NINJA: Role(
        name=RoleName.NINJA,
        team=Team.MAFIA,
        emoji="🥷",
        label="Ниндзя",
        has_night_action=True,
        is_unique=True,
        description="Ваша атака скрытна и смертоносна: она игнорирует лечение Доктора и бронежилет.",
        goal="Уничтожать самые защищенные цели города.",
    ),
    RoleName.WEREWOLF: Role(
        name=RoleName.WEREWOLF,
        team=Team.MAFIA,
        emoji="🐺",
        label="Оборотень",
        has_night_action=False,
        is_unique=True,
        description="Пока жива мафия, вы выглядите как мирный житель. Когда вся мафия погибнет, вы пробуждаетесь и начинаете убивать.",
        goal="Дождаться своего часа и стать новым кошмаром города.",
    ),
    RoleName.MANIAC: Role(
        name=RoleName.MANIAC,
        team=Team.NEUTRAL,
        emoji="🔨",
        label="Маньяк",
        has_night_action=True,
        is_unique=True,
        description="Вы действуете в одиночку. Каждую ночь вы выбираете жертву для убийства.",
        goal="Остаться последним выжившим в этом городе.",
    ),
    RoleName.JESTER: Role(
        name=RoleName.JESTER,
        team=Team.NEUTRAL,
        emoji="🃏",
        label="Шут",
        has_night_action=False,
        is_unique=True,
        description="Вы кажетесь всем подозрительным. Ваша задача — спровоцировать город на свою казнь.",
        goal="Быть повешенным на дневном голосовании.",
    ),
    RoleName.TERRORIST: Role(
        name=RoleName.TERRORIST,
        team=Team.NEUTRAL,
        emoji="💣",
        label="Террорист",
        has_night_action=False,
        is_unique=True,
        description="Если вас убьют ночью, вы заберете убийцу с собой. Если вас казнят днем — вы проиграли.",
        goal="Уничтожить своего ночного гостя.",
    ),
    RoleName.POISONER: Role(
        name=RoleName.POISONER,
        team=Team.NEUTRAL,
        emoji="☠️",
        label="Отравитель",
        has_night_action=True,
        is_unique=True,
        description="Ваш яд действует не сразу. Выбранный игрок умрет только в конце следующего дня (после обсуждения).",
        goal="Сеять смерть и хаос, наблюдая за мучениями жертв.",
    ),
    RoleName.BARTENDER: Role(
        name=RoleName.BARTENDER,
        team=Team.NEUTRAL,
        emoji="🍺",
        label="Бармен",
        has_night_action=True,
        is_unique=True,
        description="Раз в 2 ночи вы угощаете игрока особым напитком. Вы крадете его способность и применяете её сами, блокируя жертву.",
        goal="Использовать чужие таланты для своей выгоды.",
    ),
}


def get_role(name: RoleName) -> Role:
    return ALL_ROLES[name]


# Роли, которые проверяются как «мирный» при проверке Комиссара
APPEARS_CIVILIAN = {RoleName.WEREWOLF}

# Роли с покупной надбавкой (уникальные = дороже)
PURCHASABLE_ROLES: set[RoleName] = {
    r for r, role in ALL_ROLES.items() if r != RoleName.CIVILIAN
}
