"""
Матрица баланса: точный состав ролей для 4-30 игроков по ТЗ.

Нотация из ТЗ:
  Ком = COMMISSIONER, Мир = CIVILIAN, Дон = DON,
  Маф = MAFIA, Dok = DOCTOR, Путана = PROSTITUTE,
  Оборотень = WEREWOLF, Маньяк = MANIAC, Бомж = WITNESS,
  Адвокат = LAWYER, Сержант = SERGEANT, Шут = JESTER,
  Террорист = TERRORIST, Отравитель = POISONER,
  Броненосец = ARMORER, Мэр = MAYOR, Бармен = BARTENDER,
  Журналист = JOURNALIST, Ниндзя = NINJA, Некромант = NECROMANCER.
"""
from __future__ import annotations

from bot.game.roles import RoleName

C = RoleName.CIVILIAN
COM = RoleName.COMMISSIONER
SGT = RoleName.SERGEANT
DOC = RoleName.DOCTOR
PRO = RoleName.PROSTITUTE
MAY = RoleName.MAYOR
JRN = RoleName.JOURNALIST
WIT = RoleName.WITNESS
ARM = RoleName.ARMORER
NEC = RoleName.NECROMANCER
MAF = RoleName.MAFIA
DON = RoleName.DON
LAW = RoleName.LAWYER
NIN = RoleName.NINJA
WER = RoleName.WEREWOLF
MAN = RoleName.MANIAC
JES = RoleName.JESTER
TER = RoleName.TERRORIST
POI = RoleName.POISONER
BAR = RoleName.BARTENDER

# ─── Точная матрица из ТЗ ───
# Каждый список — полный состав ролей для N игроков
BALANCE_MATRIX: dict[int, list[RoleName]] = {
    4:  [COM, C, C, DON],
    5:  [COM, C, C, DON, DOC],
    6:  [COM, C, C, DON, DOC, MAF],
    7:  [COM, C, C, DON, DOC, MAF, PRO],
    8:  [COM, C, C, DON, DOC, MAF, PRO, MAF],
    9:  [COM, C, C, DON, DOC, MAF, PRO, MAF, WER],
    10: [COM, C, C, DON, DOC, MAF, PRO, MAF, WER, MAN],
    11: [COM, C, C, DON, DOC, MAF, PRO, MAF, WER, MAN, WIT],
    12: [COM, C, C, DON, DOC, MAF, PRO, MAF, WER, MAN, WIT, LAW],
    13: [COM, C, C, DON, DOC, MAF, PRO, MAF, WER, MAN, WIT, LAW, SGT],
    14: [COM, C, C, DON, DOC, MAF, PRO, MAF, WER, MAN, WIT, LAW, SGT, JES],
    15: [COM, C, C, DON, DOC, MAF, PRO, MAF, WER, MAN, WIT, LAW, SGT, JES, TER],
    16: [COM, C, C, DON, DOC, MAF, PRO, MAF, WER, MAN, WIT, LAW, SGT, JES, TER, POI],
    17: [COM, C, C, DON, DOC, MAF, PRO, MAF, WER, MAN, WIT, LAW, SGT, JES, TER, POI, ARM],
    18: [COM, C, C, DON, DOC, MAF, PRO, MAF, WER, MAN, WIT, LAW, SGT, JES, TER, POI, ARM, MAF],
    19: [COM, C, C, DON, DOC, MAF, PRO, MAF, WER, MAN, WIT, LAW, SGT, JES, TER, POI, ARM, MAF, C],
    20: [COM, C, C, DON, DOC, MAF, PRO, MAF, WER, MAN, WIT, LAW, SGT, JES, TER, POI, ARM, MAF, C, BAR],
    21: [COM, C, C, DON, DOC, MAF, PRO, MAF, WER, MAN, WIT, LAW, SGT, JES, TER, POI, ARM, MAF, C, BAR, MAY],
    22: [COM, C, C, DON, DOC, MAF, PRO, MAF, WER, MAN, WIT, LAW, SGT, JES, TER, POI, ARM, MAF, C, BAR, MAY, JRN],
    23: [COM, C, C, DON, DOC, MAF, PRO, MAF, WER, MAN, WIT, LAW, SGT, JES, TER, POI, ARM, MAF, C, BAR, MAY, JRN, NIN],
    24: [COM, C, C, DON, DOC, MAF, PRO, MAF, WER, MAN, WIT, LAW, SGT, JES, TER, POI, ARM, MAF, C, BAR, MAY, JRN, NIN, NEC],
    25: [COM, C, C, DON, DOC, MAF, PRO, MAF, WER, MAN, WIT, LAW, SGT, JES, TER, POI, ARM, MAF, C, BAR, MAY, JRN, NIN, NEC, DOC],
    26: [COM, C, C, DON, DOC, MAF, PRO, MAF, WER, MAN, WIT, LAW, SGT, JES, TER, POI, ARM, MAF, C, BAR, MAY, JRN, NIN, NEC, DOC, MAF],
    27: [COM, C, C, DON, DOC, MAF, PRO, MAF, WER, MAN, WIT, LAW, SGT, JES, TER, POI, ARM, MAF, C, BAR, MAY, JRN, NIN, NEC, DOC, MAF, C],
    28: [COM, C, C, DON, DOC, MAF, PRO, MAF, WER, MAN, WIT, LAW, SGT, JES, TER, POI, ARM, MAF, C, BAR, MAY, JRN, NIN, NEC, DOC, MAF, C, C],
    29: [COM, C, C, DON, DOC, MAF, PRO, MAF, WER, MAN, WIT, LAW, SGT, JES, TER, POI, ARM, MAF, C, BAR, MAY, JRN, NIN, NEC, DOC, MAF, C, C, MAF],
    30: [COM, C, C, DON, DOC, MAF, PRO, MAF, WER, MAN, WIT, LAW, SGT, JES, TER, POI, ARM, MAF, C, BAR, MAY, JRN, NIN, NEC, DOC, MAF, C, C, MAF, SGT],
}


def get_role_set(player_count: int) -> list[RoleName]:
    """
    Возвращает список ролей для N игроков.
    Поддерживает диапазон 4..30.
    """
    if player_count < 4:
        raise ValueError("Минимальное количество игроков: 4")
    if player_count > 30:
        raise ValueError("Максимальное количество игроков: 30")
    return list(BALANCE_MATRIX[player_count])
