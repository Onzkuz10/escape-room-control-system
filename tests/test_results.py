from backend.events import EventBus
from backend.models import Config
from backend.results import ResultStore
from backend.state import GameState


def test_results_survive_reset_and_reopening_without_duplicates(tmp_path):
    path = tmp_path / 'results.json'
    now = [100.0]
    store = ResultStore(path)
    game = GameState(Config(duration_seconds=600), EventBus(), clock=lambda: now[0], result_store=store)
    game.start()
    now[0] += 90
    game.approve_solution()
    game.reset()
    game.reset()
    assert len(ResultStore(path).results) == 1
    assert store.results[0]['outcome'] == 'solved'
    assert store.results[0]['elapsed_seconds'] == 90
    assert store.results[0]['remaining_seconds'] == 510
    game.start()
    now[0] += 35
    game.reset()
    records = ResultStore(path).results
    assert len(records) == 2
    assert records[1]['outcome'] == 'reset' and records[1]['elapsed_seconds'] == 35
    game.start()
    now[0] += 601
    game.tick()
    game.reset()
    assert ResultStore(path).results[-1]['outcome'] == 'expired'
    assert len(ResultStore(path).results) == 3
    assert 'results' not in game.snapshot(player=True)
