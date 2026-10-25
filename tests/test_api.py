import time
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import pytest
from fastapi.testclient import TestClient
from backend import main
from backend.models import Config
from backend.events import EventBus
from backend.state import GameState


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(main, 'game', GameState(Config(), EventBus()))
    monkeypatch.setattr(main, 'bus', main.game.bus)
    monkeypatch.setattr(main, 'CONFIG_FILE', tmp_path / 'config.json')
    monkeypatch.setattr(main, 'MEDIA_DIR', tmp_path / 'media')
    main.clients.clear()
    with TestClient(main.app) as c:
        yield c


def post(c, action, value=None):
    return c.post('/api/command', json={'action': action, 'value': value})


def receive_phase(ws, phase):
    for _ in range(80):
        data = ws.receive_json()['state']
        if data['phase'] == phase:
            return data
    raise AssertionError(f'Socket did not reach {phase}')


def test_two_sockets_share_timer_digits_success_and_reconnect(client):
    with client.websocket_connect('/ws?role=dashboard') as dash, client.websocket_connect('/ws?role=player') as player:
        d = dash.receive_json()['state']; p = player.receive_json()['state']
        assert d['remaining_seconds'] == p['remaining_seconds'] == 3600
        assert 'code' in d and 'code' not in p
        assert post(client,'start').status_code == 200
        assert receive_phase(dash,'running')['running']
        assert receive_phase(player,'running')['running']
        time.sleep(.12)
        assert post(client,'pause').status_code == 200
        paused = receive_phase(player,'paused')
        assert 3599 < paused['remaining_seconds'] < 3600
        for i, digit in enumerate([4, 2, 7]):
            assert post(client,'digit',{'index':i, 'digit':digit}).status_code == 200
        assert client.get('/api/state').json()['correct'] == [True,True,True,False]
        assert post(client,'digit',{'index':3, 'digit':9}).status_code == 200
        assert client.get('/api/state').json()['phase'] == 'paused'
        assert post(client, 'next_view').status_code == 200
        assert receive_phase(player,'solved')['correct'] == [True]*4
        assert receive_phase(dash,'solved')['phase'] == 'solved'
    with client.websocket_connect('/ws?role=player') as reconnected:
        assert reconnected.receive_json()['state']['phase'] == 'solved'
    assert post(client,'reset').json()['digits'] == [None]*4


def test_config_persistence_validation_and_simulation(client):
    assert post(client,'code','0012').status_code == 200
    assert main.CONFIG_FILE.exists()
    assert main.load_config().code == '0012'
    assert post(client,'digits',[0,0,1,1]).json()['correct'] == [True,True,True,False]
    assert post(client,'simulate').json()['phase'] == 'solved'
    assert post(client,'code','3456').status_code == 400
    assert post(client,'reset').status_code == 200
    assert post(client,'duration',2).json()['remaining_seconds'] == 2
    assert post(client,'code','12345').status_code == 400
    assert post(client,'digits',[True,2,3,4]).status_code == 400
    assert post(client,'digit',{'index':4,'digit':1}).status_code == 400
    assert post(client,'regions',[]).status_code == 400
    assert post(client,'camera_start',-1).status_code == 400
    assert post(client,'nonsense').status_code == 422
    assert post(client,'start').status_code == 200
    assert post(client,'duration',100).status_code == 400
    assert post(client,'code','3333').status_code == 400
    assert post(client,'mode','camera').status_code == 200
    assert post(client,'digits',[4,2,7,9]).status_code == 400


def test_failed_persistence_leaves_live_state_unchanged(client, monkeypatch):
    def fail(config): raise OSError('disk full')
    monkeypatch.setattr(main,'save_config',fail)
    assert post(client,'code','9999').status_code == 500
    assert main.game.config.code == '4279'


def test_health_and_static_routes(client):
    assert client.get('/api/health').json()['ok']
    assert client.get('/').status_code == 200
    assert client.get('/player').status_code == 200
    assert client.get('/printables/numerolaput.html').status_code == 200
    assert client.get('/printables/DigitSans.ttf').status_code == 200


class SyntheticCamera:
    """Replace only the absent hardware. Use the production OCR and stabilizer."""
    def __init__(self, config):
        image = Image.new('RGB',(1280,720),'white')
        draw = ImageDraw.Draw(image)
        font_path = Path(__file__).resolve().parents[1] / 'backend/assets/DigitSans.ttf'
        font = ImageFont.truetype(str(font_path),160)
        for r, digit in zip(config.regions, config.code):
            draw.text(((r.x+r.width/2)*1280,(r.y+r.height/2)*720),digit,anchor='mm',font=font,fill='black')
        self.frame = cv2.cvtColor(np.array(image),cv2.COLOR_RGB2BGR)
        self.status = 'on'
    def latest(self): return (self.frame.copy(),time.monotonic()) if self.status == 'on' else (None,0)
    def info(self): return {'status':self.status,'message':'Test camera','width':1280,'height':720}
    def stop(self): self.status = 'off'


def test_camera_ocr_to_player_success_end_to_end(client, monkeypatch):
    monkeypatch.setattr(main,'camera',SyntheticCamera(main.game.config))
    assert post(client,'mode','camera').status_code == 200
    assert post(client,'start').status_code == 200
    assert post(client,'next_view').status_code == 200
    with client.websocket_connect('/ws?role=player') as player:
        player.receive_json()
        result = receive_phase(player,'solved')
        assert result['digits'] == [4,2,7,9]
        assert result['correct'] == [True]*4
        assert 'code' not in result
        assert 'recognition_diagnostics' not in result
        diagnostics = client.get('/api/state').json()['recognition_diagnostics']
        assert all(d['engine'] == 'MNIST CNN (ONNX)' for d in diagnostics)
        assert all(d['input_image'].startswith('data:image/png;base64,') for d in diagnostics)
        assert all(d['roi_image'].startswith('data:image/jpeg;base64,') for d in diagnostics)


def test_camera_loss_clears_current_digits(client, monkeypatch):
    fake = SyntheticCamera(main.game.config)
    monkeypatch.setattr(main,'camera',fake)
    post(client,'mode','camera')
    main.game.set_digits([4,None,None,None],[98,None,None,None])
    fake.stop()
    time.sleep(.15)
    assert client.get('/api/state').json()['digits'] == [None]*4


def test_presentation_media_persistence_and_player_reconnection(client):
    upload = client.post('/api/media?filename=intro.gif', content=b'GIF89a')
    assert upload.status_code == 200
    gif = upload.json()['url']
    music = client.post('/api/media?filename=calm.mp3', content=b'ID3test').json()['url']
    presentation = {'slides': [{'title': 'Alku', 'body': 'Ohjeet', 'media': gif}, {'title': 'Valmiina?'}],
                    'pregame_music': music, 'volume': 0.4}
    presentation['slides'] = [s.model_dump() for s in main.game.config.presentation.slides if s.locked] + presentation['slides']
    assert post(client, 'presentation', presentation).status_code == 200
    assert main.load_config().presentation.pregame_music == music
    assert client.get(gif).headers['content-type'] == 'image/gif'
    assert client.get(music).content == b'ID3test'
    assert post(client, 'pregame').json()['remaining_seconds'] == 3600
    assert post(client, 'next_slide').json()['slide_index'] == 1
    with client.websocket_connect('/ws?role=player') as player:
        snapshot = player.receive_json()['state']
        assert snapshot['phase'] == 'pregame' and snapshot['slide_index'] == 1
        assert snapshot['presentation']['slides'][2]['media'] == gif
        assert snapshot['presentation']['pregame_music'] == music
        assert 'code' not in snapshot
    assert post(client, 'start').json()['game_view'] == 'timer'
    assert post(client, 'presentation', presentation).status_code == 400
    assert client.post('/api/media?filename=late.mp3', content=b'test').status_code == 400
    assert post(client, 'next_slide').status_code == 400
    post(client, 'digits', [4, 2, 7, 9])
    assert client.get('/api/state').json()['phase'] == 'running'
    assert post(client, 'next_view').json()['phase'] == 'solved'


def test_media_and_presentation_validation(client, monkeypatch):
    assert client.post('/api/media?filename=bad.html', content=b'bad').status_code == 400
    assert client.post('/api/media?filename=empty.mp3', content=b'').status_code == 400
    monkeypatch.setattr(main, 'MAX_MEDIA_SIZE', 4)
    assert client.post('/api/media?filename=large.mp3', content=b'12345').status_code == 413
    assert list(main.MEDIA_DIR.iterdir()) == []
    assert post(client, 'presentation', {'slides': []}).status_code == 400
    assert post(client, 'presentation', {'volume': 2}).status_code == 400
    assert post(client, 'presentation', {'pregame_music': 'https://example.com/file.mp3'}).status_code == 400
    assert post(client, 'presentation', {'pregame_music': '/media/' + 'a' * 32 + '.mp3'}).status_code == 400
    assert post(client, 'presentation', {'slides': [{'media': '/media/../../config.json'}]}).status_code == 400
    assert post(client, 'next_view').status_code == 400
    assert client.get('/media/missing.mp3').status_code == 404


def test_camera_list_start_high_index_and_disconnection(client, monkeypatch):
    devices = [{'index': 12, 'name': 'USB Camera'}]
    monkeypatch.setattr(main, 'camera_devices', lambda: devices.copy())
    started = []
    monkeypatch.setattr(main.camera, 'start', started.append)
    assert client.get('/api/cameras').json() == {'devices': devices}
    assert post(client, 'camera_start', 12).status_code == 200
    assert started == [12] and main.load_config().camera_index == 12
    devices.clear()
    assert client.get('/api/cameras').json() == {'devices': []}
    assert post(client, 'camera_start', 12).status_code == 400
    assert started == [12]


def test_camera_discovery_failure_is_actionable(client, monkeypatch):
    def fail():
        raise RuntimeError('native discovery unavailable')
    monkeypatch.setattr(main, 'camera_devices', fail)
    response = client.get('/api/cameras')
    assert response.status_code == 503
    assert 'Kameroiden haku' in response.json()['detail']


def test_previous_view_api(client):
    assert post(client, 'previous_view').status_code == 400
    assert post(client, 'start').status_code == 200
    assert post(client, 'next_view').json()['game_view'] == 'digits'
    response = post(client, 'previous_view')
    assert response.status_code == 200
    assert response.json()['game_view'] == 'timer'
    assert response.json()['running']


def test_result_videos_and_seating_layout_persist_and_reach_player(client):
    victory = client.post('/api/media?filename=win.mp4', content=b'test-video').json()['url']
    defeat = client.post('/api/media?filename=lose.webm', content=b'test-video').json()['url']
    presentation = {'victory_video': victory, 'defeat_video': defeat,
                    'slides': [{'title': 'Poytiin', 'layout': 'seating'}]}
    presentation['slides'] = [s.model_dump() for s in main.game.config.presentation.slides if s.locked] + presentation['slides']
    assert post(client, 'presentation', presentation).status_code == 200
    assert main.load_config().presentation.victory_video == victory
    assert main.load_config().presentation.defeat_video == defeat
    with client.websocket_connect('/ws?role=player') as player:
        snapshot = player.receive_json()['state']['presentation']
        assert snapshot['victory_video'] == victory
        assert snapshot['defeat_video'] == defeat
        assert snapshot['slides'][0]['layout'] == 'seating'
    assert post(client, 'presentation', {'victory_video': '/media/' + 'f' * 32 + '.mp4'}).status_code == 400
    assert post(client, 'presentation', {'defeat_video': victory.replace('.mp4', '.wav')}).status_code == 400
    assert post(client, 'presentation', {'slides': [{'layout': 'unknown'}]}).status_code == 400


def test_human_approval_setting_and_emergency_api(client):
    assert post(client, 'require_human_approval', True).status_code == 200
    assert main.load_config().require_human_approval
    assert post(client, 'require_human_approval', 1).status_code == 400
    assert post(client, 'approve_solution').status_code == 400
    post(client, 'start')
    post(client, 'next_view')
    assert post(client, 'digits', [4, 2, 7, 9]).json()['phase'] == 'running'
    assert post(client, 'approve_solution').json()['phase'] == 'solved'
    assert post(client, 'require_human_approval', False).status_code == 400
    post(client, 'reset')
    assert client.get('/api/state').json()['require_human_approval'] is True
    assert post(client, 'require_human_approval', False).status_code == 200


def test_result_video_control_reaches_player_and_reconnection(client):
    video = client.post('/api/media?filename=win.mp4', content=b'test-video').json()['url']
    assert post(client, 'presentation', {'victory_video': video, 'defeat_video': video,
        'slides': [s.model_dump() for s in main.game.config.presentation.slides if s.locked] + [{'title': 'Ratkaiskaa koodi.', 'layout': 'code'}]}).status_code == 200
    post(client, 'start')
    result = post(client, 'approve_solution').json()
    assert result['phase'] == 'solved' and not result['result_video_playing']
    assert post(client, 'next_view').json()['result_video_playing']
    with client.websocket_connect('/ws?role=player') as player:
        snapshot = player.receive_json()['state']
        assert snapshot['phase'] == 'solved' and snapshot['result_video_playing']
        assert snapshot['presentation']['slides'][2]['layout'] == 'code'
    assert not post(client, 'previous_view').json()['result_video_playing']
    assert not post(client, 'reset').json()['result_video_playing']


def test_live_volume_is_persistent_without_changing_game_state(client):
    post(client, 'start')
    post(client, 'pause')
    post(client, 'digits', [1, 2, 3, 4])
    before = main.game.snapshot()
    result = post(client, 'audio_settings', {'volume': .12, 'muted': True})
    assert result.status_code == 200
    after = result.json()
    for key in ('phase', 'running', 'remaining_seconds', 'digits', 'game_view'):
        assert after[key] == before[key]
    assert main.load_config().presentation.volume == .12
    assert main.load_config().presentation.muted
    for bad in ({'volume': 2}, {'volume': True}, {'muted': 'yes'}, {'code': '1234'}):
        assert post(client, 'audio_settings', bad).status_code == 400


def test_settings_save_and_portable_bundle_import(client):
    assert post(client, 'game_settings', {'code': '0012', 'duration_seconds': 500, 'require_human_approval': True}).status_code == 200
    music = client.post('/api/media?filename=music.mp3', content=b'ID3test').json()['url']
    presentation = main.game.config.presentation.model_dump()
    presentation['game_music'] = music
    assert post(client, 'presentation', presentation).status_code == 200
    exported = client.get('/api/settings/export')
    assert exported.status_code == 200
    assert exported.headers['content-type'] == 'application/zip'
    post(client, 'game_settings', {'code': '9876', 'duration_seconds': 100})
    imported = client.post('/api/settings/import', content=exported.content)
    assert imported.status_code == 200
    value = imported.json()
    assert value['code'] == '0012' and value['remaining_seconds'] == 500
    assert value['phase'] == 'ready' and value['require_human_approval']
    new_music = value['presentation']['game_music']
    assert new_music != music and client.get(new_music).content == b'ID3test'
    post(client, 'start')
    assert client.post('/api/settings/import', content=exported.content).status_code == 400
    assert post(client, 'game_settings', {'code': '3333'}).status_code == 400


def test_locked_intro_cannot_be_removed_reordered_or_reanimated(client):
    slides = main.game.config.presentation.model_dump()['slides']
    assert post(client, 'presentation', {'slides': [slide for slide in slides if not slide['locked']]}).status_code == 400
    assert post(client, 'presentation', {'slides': [slides[0], slides[2], slides[1], *slides[3:]]}).status_code == 400
    slides[1]['animation'] = 'float'
    assert post(client, 'presentation', {'slides': slides}).status_code == 400


def test_solution_is_only_revealed_after_win(client):
    assert client.get('/api/state').json()['solution_digits'] is None
    post(client, 'start')
    with client.websocket_connect('/ws?role=player') as player:
        assert player.receive_json()['state']['solution_digits'] is None
    result = post(client, 'approve_solution').json()
    assert result['solution_digits'] == [4, 2, 7, 9]
    assert result['result_at'] is not None and not result['result_video_playing']


def test_unicode_settings_and_legacy_windows_config(client):
    config = main.game.config.model_copy(deep=True)
    config.presentation.slides[2].title = 'Ääni ja pöydät 🎛️'
    main.save_config(config)
    assert '🎛️' in main.CONFIG_FILE.read_text(encoding='utf-8')
    assert main.load_config().presentation.slides[2].title == config.presentation.slides[2].title
    config.presentation.slides[2].title = 'Ääni ja pöydät'
    main.CONFIG_FILE.write_text(config.model_dump_json(), encoding='cp1252')
    assert main.load_config().presentation.slides[2].title == 'Ääni ja pöydät'


def test_import_persistence_failure_removes_new_media_without_overwriting_settings(client, monkeypatch):
    music = client.post('/api/media?filename=music.mp3', content=b'ID3test').json()['url']
    presentation = main.game.config.presentation.model_dump()
    presentation['game_music'] = music
    post(client, 'presentation', presentation)
    archive = client.get('/api/settings/export').content
    files_before = set(main.MEDIA_DIR.iterdir())
    def fail(config):
        raise OSError('disk full')
    monkeypatch.setattr(main, 'save_config', fail)
    assert client.post('/api/settings/import', content=archive).status_code == 500
    assert set(main.MEDIA_DIR.iterdir()) == files_before
    assert main.game.config.presentation.game_music == music


def test_partial_correctness_is_hidden_from_player_websocket(client):
    post(client, 'start')
    post(client, 'next_view')
    post(client, 'digits', [4, 2, 7, 8])
    with client.websocket_connect('/ws?role=player') as player:
        snapshot = player.receive_json()['state']
        assert snapshot['game_view'] == 'digits'
        assert snapshot['digits'] == [4, 2, 7, 8]
        assert snapshot['correct'] == [False] * 4
        assert snapshot['solution_digits'] is None
    assert client.get('/api/state').json()['correct'] == [True, True, True, False]


def test_victory_sound_choices_require_operator_selection_and_persist(client):
    uploaded = client.post('/api/victory-sounds?filename=variant.wav&duration_seconds=4', content=b'RIFFtest')
    assert uploaded.status_code == 200
    presentation = uploaded.json()['presentation']
    assert presentation['victory_sound'] is None
    assert len(presentation['victory_sounds']) == 1
    sound = presentation['victory_sounds'][0]
    assert sound['name'] == 'Vaihtoehto 1'
    assert client.get(sound['file']).content == b'RIFFtest'
    post(client, 'start')
    post(client, 'pause')
    before = main.game.snapshot()
    selected = post(client, 'victory_sound', sound['file'])
    assert selected.status_code == 200
    for key in ('phase', 'remaining_seconds', 'digits', 'game_view'):
        assert selected.json()[key] == before[key]
    assert main.load_config().presentation.victory_sound == sound['file']
    assert post(client, 'victory_sound', '/media/' + 'f' * 32 + '.wav').status_code == 400
    assert post(client, 'victory_sound', None).json()['presentation']['victory_sound'] is None


def test_victory_sound_library_limits_and_invalid_uploads(client):
    assert client.post('/api/victory-sounds?filename=file.exe', content=b'test').status_code == 400
    assert client.post('/api/victory-sounds?filename=file.wav&duration_seconds=31', content=b'test').status_code == 422
    assert client.post('/api/victory-sounds?filename=file.wav', content=b'').status_code == 400
    for index in range(4):
        result = client.post('/api/victory-sounds?filename=file.mp3', content=b'ID3test')
        assert result.status_code == 200
        assert len(result.json()['presentation']['victory_sounds']) == index + 1
    files = set(main.MEDIA_DIR.iterdir())
    assert client.post('/api/victory-sounds?filename=file.mp3', content=b'ID3test').status_code == 400
    assert set(main.MEDIA_DIR.iterdir()) == files


def test_sound_variants_and_selection_are_portable(client):
    result = client.post('/api/victory-sounds?filename=one.wav', content=b'RIFF-one').json()
    one = result['presentation']['victory_sounds'][0]['file']
    client.post('/api/victory-sounds?filename=two.wav', content=b'RIFF-two')
    post(client, 'victory_sound', one)
    archive = client.get('/api/settings/export')
    imported = client.post('/api/settings/import', content=archive.content)
    assert imported.status_code == 200
    presentation = imported.json()['presentation']
    assert len(presentation['victory_sounds']) == 2
    assert presentation['victory_sound'] == presentation['victory_sounds'][0]['file']
    assert presentation['victory_sound'] != one
    assert client.get(presentation['victory_sound']).content == b'RIFF-one'


def test_failed_sound_save_does_not_add_or_leave_a_file(client, monkeypatch):
    def fail(config):
        raise OSError('disk full')
    monkeypatch.setattr(main, 'save_config', fail)
    assert client.post('/api/victory-sounds?filename=file.wav', content=b'RIFF').status_code == 500
    assert main.game.config.presentation.victory_sounds == []
    assert list(main.MEDIA_DIR.iterdir()) == []


def test_welcome_precedes_intact_locked_intro_pair(client):
    slides = client.get('/api/state').json()['presentation']['slides']
    assert slides[0]['title'] == 'Tervetuloa pakohuoneeseen!'
    assert slides[0]['layout'] == 'text' and not slides[0]['locked']
    assert [s['layout'] for s in slides[1:3]] == ['seating', 'movement']
    assert post(client, 'presentation', {'slides': slides}).status_code == 200
    split_pair = [slides[1], slides[0], slides[2], *slides[3:]]
    assert post(client, 'presentation', {'slides': split_pair}).status_code == 400
    post(client, 'pregame')
    assert client.get('/api/state').json()['slide_index'] == 0
    assert post(client, 'next_slide').json()['slide_index'] == 1
    assert post(client, 'next_slide').json()['slide_index'] == 2


def test_slot_icons_persist_and_reach_player_without_following_digits(client):
    icons = ['shovel', None, 'math', 'car']
    response = post(client, 'game_settings', {'slot_icons': icons})
    assert response.status_code == 200
    assert response.json()['code'] == '4279'
    assert main.load_config().slot_icons == icons
    post(client, 'start')
    post(client, 'next_view')
    post(client, 'digits', [1, 9, 0, 3])
    with client.websocket_connect('/ws?role=player') as player:
        snapshot = player.receive_json()['state']
        assert snapshot['slot_icons'] == icons
        assert snapshot['digits'] == [1, 9, 0, 3]
        assert snapshot['correct'] == [False] * 4
        assert 'code' not in snapshot
    assert post(client, 'game_settings', {'slot_icons': [None] * 4}).status_code == 400
    assert post(client, 'reset').json()['slot_icons'] == icons
    assert post(client, 'game_settings', {'code': '3590'}).json()['slot_icons'] == icons


@pytest.mark.parametrize('icons', [[], [None] * 3, [None] * 5,
    ['clock', 'golf', 'car', None], [False, None, None, None], 'math', None])
def test_invalid_slot_icons_do_not_change_saved_configuration(client, icons):
    before = main.game.config.model_dump()
    assert post(client, 'game_settings', {'slot_icons': icons}).status_code == 400
    assert main.game.config.model_dump() == before
    assert not main.CONFIG_FILE.exists()


def test_empty_slot_icons_are_portable_and_old_configs_get_clock_defaults(client):
    assert Config.model_validate({'code': '3590'}).slot_icons == ['math', 'golf', 'car', 'shovel']
    icons = [None, 'golf', None, 'shovel']
    assert post(client, 'game_settings', {'slot_icons': icons}).status_code == 200
    archive = client.get('/api/settings/export')
    post(client, 'game_settings', {'slot_icons': [None] * 4})
    imported = client.post('/api/settings/import', content=archive.content)
    assert imported.status_code == 200
    assert imported.json()['slot_icons'] == icons
    assert main.load_config().slot_icons == icons


def test_slot_icon_save_failure_keeps_previous_icons(client, monkeypatch):
    before = list(main.game.config.slot_icons)
    def fail(config):
        raise OSError('disk full')
    monkeypatch.setattr(main, 'save_config', fail)
    assert post(client, 'game_settings', {'slot_icons': [None] * 4}).status_code == 500
    assert main.game.config.slot_icons == before
