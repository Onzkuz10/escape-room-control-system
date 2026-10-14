import pytest
from pydantic import ValidationError
from backend.audio import AudioManager
from backend.events import EventBus
from backend.models import Config, Region
from backend.state import GameState


@pytest.fixture
def room():
    now = [100.]
    bus = EventBus()
    audio = AudioManager(bus)
    state = GameState(Config(duration_seconds=600), bus, lambda: now[0])
    return state, now, bus, audio


def test_countdown_pause_resume_uses_monotonic_clock(room):
    state, now, bus, audio = room
    state.start()
    now[0] += 12.25
    state.pause()
    assert state.remaining == 587.75
    now[0] += 1000
    state.tick()
    assert state.remaining == 587.75
    state.start()
    now[0] += 87.75
    state.tick()
    assert state.remaining == 500
    assert audio.cue == 'tension'


def test_correct_positions_and_latched_success(room):
    state, now, bus, audio = room
    state.start()
    now[0] += 5
    state.set_digits([4, 2, None, 8])
    assert state.correct() == [True, True, False, False]
    assert state.phase == 'running'
    state.set_digits([4, 2, 7, 9])
    assert state.phase == 'solved' and not state.running
    assert state.remaining == 595
    assert audio.cue == 'victory'
    now[0] += 5000
    state.set_digits([None] * 4)
    state.tick()
    assert state.digits == [4, 2, 7, 9]
    assert state.remaining == 595
    assert sum(e['type'] == 'game.solved' for e in bus.history) == 1
    with pytest.raises(ValueError):
        state.start()
    state.reset()
    assert state.phase == 'ready' and state.digits == [None] * 4
    assert state.remaining == 600 and audio.cue == 'idle'


def test_expiry_wins_against_late_correct_code(room):
    state, now, bus, audio = room
    state.start()
    now[0] += 600.01
    state.set_digits([4, 2, 7, 9])
    assert state.phase == 'expired' and state.remaining == 0
    assert audio.cue == 'timeout'
    assert not any(e['type'] == 'game.solved' for e in bus.history)
    assert sum(e['type'] == 'timer.expired' for e in bus.history) == 1


def test_warning_fires_once_and_subscriber_failure_is_isolated(room):
    state, now, bus, audio = room
    bus.subscribe(lambda event: (_ for _ in ()).throw(RuntimeError('test adapter failure')))
    state.start()
    now[0] += 301
    state.tick()
    state.pause()
    state.start()
    now[0] += 1
    state.tick()
    assert sum(e['type'] == 'timer.warning' for e in bus.history) == 1


def test_player_snapshot_has_no_secret_config(room):
    state, *_ = room
    snapshot = state.snapshot(player=True)
    for field in ('code', 'regions', 'camera', 'events', 'confidences'):
        assert field not in snapshot
    assert 'remaining_seconds' in snapshot


@pytest.mark.parametrize('kwargs', [{'code':'123'}, {'code':'١٢٣٤'}, {'duration_seconds':0}, {'regions':[]}, {'camera_index':10}])
def test_invalid_configuration_rejected(kwargs):
    with pytest.raises(ValidationError):
        Config(**kwargs)


def test_region_must_fit_inside_frame():
    with pytest.raises(ValidationError):
        Region(x=.9, y=.2, width=.3, height=.5)


def test_camera_cannot_solve_with_a_held_but_currently_uncertain_digit(room):
    state, *_ = room
    state.set_digits([4,2,7,9],allow_solve=False)
    assert state.correct() == [True]*4
    assert state.phase == 'ready'
    state.set_digits([4,2,7,9],allow_solve=True)
    assert state.phase == 'solved'
