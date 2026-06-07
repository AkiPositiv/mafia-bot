"""
Test _check_win logic to verify game ends correctly.
"""
import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.game.engine import GameEngine, PlayerState
from bot.game.roles import RoleName, Team, ALL_ROLES


async def test_check_win():
    """Test various win condition scenarios."""
    
    # Track what happened
    events_fired = []
    
    async def mock_notify(event: str, data: dict):
        events_fired.append((event, data))
        print(f"  EVENT FIRED: {event} -> {data.get('winner', 'N/A')}")
    
    # ── Test 1: Town wins (2 town, 0 mafia) ──
    print("\n=== TEST 1: 2 Town, 0 Mafia ===")
    engine = GameEngine(1, 1, mock_notify)
    engine.players[100] = PlayerState(user_id=100, username="TownA", role=RoleName.CIVILIAN, is_alive=True)
    engine.players[200] = PlayerState(user_id=200, username="TownB", role=RoleName.COMMISSIONER, is_alive=True)
    engine.players[300] = PlayerState(user_id=300, username="DonDead", role=RoleName.DON, is_alive=False)
    
    events_fired.clear()
    result = await engine._check_win()
    print(f"  _check_win returned: {result}")
    print(f"  Events: {events_fired}")
    assert result == True, "Should return True (town wins)"
    assert len(events_fired) > 0, "Should fire game_finished event"
    assert events_fired[0][1]["winner"] == "town", "Winner should be 'town'"
    
    # Check snapshot role is string
    snapshot = events_fired[0][1]["snapshot"]
    for p in snapshot:
        print(f"  Snapshot role type: {type(p['role'])} value: {p['role']}")
        assert isinstance(p["role"], str), f"Role should be string, got {type(p['role'])}"
    
    # ── Test 2: Mafia wins (1v1) ──
    print("\n=== TEST 2: 1 Mafia vs 1 Town (1v1) ===")
    engine2 = GameEngine(2, 2, mock_notify)
    engine2.players[100] = PlayerState(user_id=100, username="TownA", role=RoleName.CIVILIAN, is_alive=True)
    engine2.players[200] = PlayerState(user_id=200, username="Don", role=RoleName.DON, is_alive=True)
    
    events_fired.clear()
    result = await engine2._check_win()
    print(f"  _check_win returned: {result}")
    assert result == True, "1v1 → mafia wins"
    assert events_fired[0][1]["winner"] == "mafia"
    
    # ── Test 3: Mafia wins (2v2) ──
    print("\n=== TEST 3: 2 Mafia vs 2 Town (2v2) ===")
    engine3 = GameEngine(3, 3, mock_notify)
    engine3.players[100] = PlayerState(user_id=100, username="TownA", role=RoleName.CIVILIAN, is_alive=True)
    engine3.players[200] = PlayerState(user_id=200, username="TownB", role=RoleName.DOCTOR, is_alive=True)
    engine3.players[300] = PlayerState(user_id=300, username="Don", role=RoleName.DON, is_alive=True)
    engine3.players[400] = PlayerState(user_id=400, username="Mafia", role=RoleName.MAFIA, is_alive=True)
    
    events_fired.clear()
    result = await engine3._check_win()
    print(f"  _check_win returned: {result}")
    assert result == True, "2v2 → mafia wins"
    assert events_fired[0][1]["winner"] == "mafia"
    
    # ── Test 4: Game continues (3 town vs 1 mafia) ──
    print("\n=== TEST 4: 3 Town vs 1 Mafia (game continues) ===")
    engine4 = GameEngine(4, 4, mock_notify)
    engine4.players[100] = PlayerState(user_id=100, username="TownA", role=RoleName.CIVILIAN, is_alive=True)
    engine4.players[200] = PlayerState(user_id=200, username="TownB", role=RoleName.DOCTOR, is_alive=True)
    engine4.players[300] = PlayerState(user_id=300, username="TownC", role=RoleName.COMMISSIONER, is_alive=True)
    engine4.players[400] = PlayerState(user_id=400, username="Don", role=RoleName.DON, is_alive=True)
    
    events_fired.clear()
    result = await engine4._check_win()
    print(f"  _check_win returned: {result}")
    assert result == False, "3v1 → game continues"
    assert len(events_fired) == 0, "Should not fire game_finished"
    
    # ── Test 5: Simulate trial execution ending game ──
    print("\n=== TEST 5: Trial execution -> Town should win ===")
    engine5 = GameEngine(5, 5, mock_notify)
    engine5.players[100] = PlayerState(user_id=100, username="TownA", role=RoleName.CIVILIAN, is_alive=True)
    engine5.players[200] = PlayerState(user_id=200, username="TownB", role=RoleName.COMMISSIONER, is_alive=True)
    engine5.players[300] = PlayerState(user_id=300, username="Don", role=RoleName.DON, is_alive=True)
    
    # Simulate trial execution of Don
    engine5.trial_target = 300
    engine5.trial_votes = {100: True, 200: True}  # both vote to execute
    engine5.phase = "trial"
    
    events_fired.clear()
    print("  Calling _end_trial()...")
    try:
        await engine5._end_trial()
    except Exception as e:
        print(f"  ❌ EXCEPTION in _end_trial: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"  Phase after _end_trial: {engine5.phase}")
    print(f"  Don is_alive: {engine5.players[300].is_alive}")
    print(f"  Events fired: {[(e[0], e[1].get('winner', 'N/A')) for e in events_fired]}")
    
    # Check that game_finished was fired
    game_finished_events = [e for e in events_fired if e[0] == "game_finished"]
    assert len(game_finished_events) > 0, "game_finished should have been fired!"
    assert game_finished_events[0][1]["winner"] == "town"
    
    print("\n✅ ALL TESTS PASSED!")


if __name__ == "__main__":
    asyncio.run(test_check_win())
