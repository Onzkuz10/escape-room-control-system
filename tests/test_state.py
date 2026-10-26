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


def test_game_start_timestamp_is_shared_and_not_reset_on_resume(room):
    state, now, *_ = room
    state.pregame()
    assert state.snapshot(player=True)['game_started_at'] is None
    state.start()
    started = state.snapshot(player=True)['game_started_at']
    assert started is not None and state.snapshot()['game_started_at'] == started
    state.pause()
    now[0] += 3
    state.start()
    assert state.snapshot()['game_started_at'] == started
    state.reset()
    assert state.snapshot()['game_started_at'] is None


def test_correct_positions_and_latched_success(room):
    state, now, bus, audio = room
    state.start()
    now[0] += 5
    state.set_digits([4, 2, None, 8])
    assert state.correct() == [True, True, False, False]
    assert state.phase == 'running'
    state.set_digits([4, 2, 7, 9])
    assert state.phase == 'running'
    assert state.snapshot(player=True)['correct'] == [False] * 4
    state.next_view()
    assert state.game_view == 'lights_off' and state.phase == 'running'
    state.next_view()
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
    state.next_view()
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


@pytest.mark.parametrize('kwargs', [{'code':'123'}, {'code':'١٢٣٤'}, {'duration_seconds':0}, {'regions':[]}, {'camera_index':-1}])
def test_invalid_configuration_rejected(kwargs):
    with pytest.raises(ValidationError):
        Config(**kwargs)


def test_region_must_fit_inside_frame():
    with pytest.raises(ValidationError):
        Region(x=.9, y=.2, width=.3, height=.5)


def test_camera_cannot_solve_with_a_held_but_currently_uncertain_digit(room):
    state, *_ = room
    state.mode = 'camera'
    state.start()
    state.next_view()
    state.next_view()
    state.set_digits([4,2,7,9],allow_solve=False)
    assert state.correct() == [True]*4
    assert state.phase == 'running'
    state.set_digits([4,2,7,9],allow_solve=True)
    assert state.phase == 'solved'


def test_pregame_does_not_run_timer_or_solve_and_resets_slide(room):
    state, now, bus, audio = room
    state.pregame()
    assert audio.cue == 'calm'
    now[0] += 300
    state.tick()
    state.set_digits([4, 2, 7, 9])
    assert state.phase == 'pregame' and not state.running and state.remaining == 600
    assert state.snapshot(player=True)['correct'] == [False] * 4
    state.change_slide(1)
    assert state.slide_index == 1
    state.change_slide(1)
    assert state.slide_index == 2
    state.change_slide(1)
    assert state.slide_index == 3
    state.change_slide(1)
    assert state.slide_index == 3
    state.start()
    assert state.digits == [None] * 4
    now[0] += 7
    state.tick()
    assert state.remaining == 593 and state.game_view == 'timer'
    with pytest.raises(ValueError):
        state.pregame()
    with pytest.raises(ValueError):
        state.change_slide(-1)
    state.reset()
    assert state.slide_index == 0 and state.game_view == 'timer'


def test_view_changes_keep_countdown_and_gate_automatic_solution(room):
    state, now, *_ = room
    state.start()
    state.set_digits([4, 2, 7, 8])
    now[0] += 10
    state.next_view()
    assert state.remaining == 590 and state.running
    assert state.game_view == 'lights_off'
    assert state.snapshot(player=True)['correct'] == [False] * 4
    assert state.snapshot()['correct'] == [True, True, True, False]
    state.set_digits([4, 2, 7, 9])
    assert state.running and state.snapshot(player=True)['correct'] == [False] * 4
    state.next_view()
    assert state.phase == 'solved' and state.remaining == 590


def test_previous_view_returns_to_timer_without_resetting_game(room):
    state, now, *_ = room
    with pytest.raises(ValueError):
        state.previous_view()
    state.start()
    state.set_digits([4, 2, 7, 8])
    state.next_view()
    now[0] += 12
    state.previous_view()
    assert state.game_view == 'timer' and state.running and state.remaining == 588
    assert state.digits == [4, 2, 7, 8]
    assert state.snapshot(player=True)['correct'] == [False] * 4
    state.pause()
    state.next_view()
    state.next_view()
    state.previous_view()
    assert state.game_view == 'lights_off'
    state.previous_view()
    assert state.phase == 'paused' and state.game_view == 'timer'


def test_human_approval_blocks_automatic_win_and_override_keeps_digits(room):
    state, now, bus, *_ = room
    state.config.require_human_approval = True
    state.start()
    state.next_view()
    state.set_digits([4, 2, 7, 9])
    assert state.phase == 'running'
    now[0] += 8
    state.approve_solution()
    assert state.phase == 'solved' and not state.running and state.remaining == 592
    assert state.digits == [4, 2, 7, 9]
    assert bus.history[0]['payload']['approved_by_operator']


def test_emergency_approval_can_override_missing_camera_digits_but_not_expiry(room):
    state, now, *_ = room
    with pytest.raises(ValueError):
        state.approve_solution()
    state.start()
    state.approve_solution()
    assert state.phase == 'solved' and state.digits == [None] * 4
    state.reset()
    state.start()
    now[0] += 601
    with pytest.raises(ValueError):
        state.approve_solution()
    assert state.phase == 'expired'


@pytest.mark.parametrize('outcome', ['solved', 'expired'])
def test_result_video_waits_for_next_view_and_reset_clears_it(room, outcome):
    state, now, *_ = room
    state.config.presentation.victory_video = '/media/' + 'a' * 32 + '.mp4'
    state.config.presentation.defeat_video = '/media/' + 'b' * 32 + '.mp4'
    state.start()
    if outcome == 'solved':
        state.approve_solution()
    else:
        now[0] += 601
        state.tick()
    remaining = state.remaining
    assert state.phase == outcome and not state.result_video_playing
    assert not state.snapshot(player=True)['result_video_playing']
    state.next_view()
    assert state.result_video_playing and state.remaining == remaining
    assert state.snapshot(player=True)['result_video_playing']
    state.previous_view()
    assert not state.result_video_playing and state.phase == outcome
    state.next_view()
    state.reset()
    assert not state.result_video_playing


def test_result_without_selected_video_stays_visible(room):
    state, *_ = room
    state.start()
    state.approve_solution()
    with pytest.raises(ValueError):
        state.next_view()
    assert state.phase == 'solved' and not state.result_video_playing


@pytest.mark.parametrize('phase', ['ready', 'pregame', 'running', 'paused', 'expired'])
@pytest.mark.parametrize('view', ['timer', 'digits'])
def test_player_never_gets_partial_correctness_before_solution(room, phase, view):
    state, *_ = room
    state.phase = phase
    state.game_view = view
    state.digits = [4, 2, 7, 8]
    assert state.snapshot()['correct'] == [True, True, True, False]
    player = state.snapshot(player=True)
    assert player['correct'] == [False] * 4
    assert player['solution_digits'] is None
    assert player['digits'] == [4, 2, 7, 8]


def test_even_a_correct_code_waiting_for_operator_gives_no_player_hints(room):
    state, *_ = room
    state.config.require_human_approval = True
    state.start()
    state.next_view()
    state.set_digits([4, 2, 7, 9])
    assert state.phase == 'running'
    assert state.snapshot()['correct'] == [True] * 4
    assert state.snapshot(player=True)['correct'] == [False] * 4
    state.approve_solution()
    assert state.snapshot(player=True)['solution_digits'] == [4, 2, 7, 9]
