"""
Day vote handler — обрабатывает голосование в группе.
"""
from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

from bot.game import registry

router = Router()


@router.callback_query(F.data.startswith("vote:"))
async def cb_vote(callback: CallbackQuery):
    """Получить голос от игрока (теперь и из ЛС)."""
    parts = callback.data.split(":")
    game_id = int(parts[1])
    target = parts[2]

    # Ищем игру по ID (так как сообщение может быть в ЛС)
    engine = registry.get_by_game_id(game_id)
    if not engine or engine.phase != "vote":
        await callback.answer("Голосование не идёт.", show_alert=True)
        return

    voter_id = callback.from_user.id
    voter = engine.players.get(voter_id)
    if not voter or not voter.is_alive:
        await callback.answer("❌ Вы не участвуете в этой игре или мертвы.", show_alert=True)
        return

    if target == "skip":
        # Если воздержался — просто помечаем как "проголосовал" для чата
        if engine.add_vote(voter_id, 0): # 0 или специальный ID для скипа
             await callback.answer("✅ Вы воздержались.")
             # Для красоты: обновим сообщение в ЛС
             await callback.message.edit_text("⚖️ Вы воздержались от голосования.")
        else:
             await callback.answer("Вы уже проголосовали!", show_alert=True)
        return

    target_id = int(target)
    target_p = engine.players.get(target_id)
    if not target_p or not target_p.is_alive:
        await callback.answer("❌ Этот игрок мёртв.", show_alert=True)
        return

    if engine.add_vote(voter_id, target_id):
        from bot.game.roles import RoleName
        weight = 2 if voter.role == RoleName.MAYOR else 1
        weight_str = f" (+{weight} голос{'а' if weight == 2 else ''})" if weight > 1 else ""
        await callback.answer(f"✅ Ваш голос за {target_p.username}{weight_str} учтён!")
        await callback.message.edit_text(f"⚖️ Вы проголосовали против {target_p.username}.")
    else:
        await callback.answer("Вы уже проголосовали!", show_alert=True)
@router.callback_query(F.data.startswith("trial_vote:"))
async def cb_trial_vote(callback: CallbackQuery):
    """Голос в суде (Лайк/Дизлайк) — обновляет счётчик в реальном времени."""
    parts = callback.data.split(":")
    game_id = int(parts[1])
    vote_str = parts[2]
    
    engine = registry.get_by_game_id(game_id)
    if not engine or engine.phase != "trial":
        await callback.answer("Суд не идёт.", show_alert=True)
        return
        
    user_id = callback.from_user.id
    vote = True if vote_str == "like" else False
    
    if engine.submit_trial_vote(user_id, vote):
        decision = "👍 повесить" if vote else "👎 помиловать"
        await callback.answer(f"✅ Ваш голос ({decision}) принят!")
        
        # Обновляем кнопки с текущими счётчиками
        likes = sum(1 for v in engine.trial_votes.values() if v is True)
        dislikes = sum(1 for v in engine.trial_votes.values() if v is False)
        from bot.keyboards.game_kb import trial_keyboard
        kb = trial_keyboard(engine.game_id, likes, dislikes)
        try:
            await callback.message.edit_reply_markup(reply_markup=kb)
        except Exception:
            pass  # сообщение уже удалено или не изменилось
    else:
        await callback.answer("❌ Вы не можете голосовать (возможно, вы мертвы).", show_alert=True)
