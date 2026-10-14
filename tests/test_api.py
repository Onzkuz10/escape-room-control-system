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
    with client.websocket_connect('/ws?role=player') as player:
        player.receive_json()
        result = receive_phase(player,'solved')
        assert result['digits'] == [4,2,7,9]
        assert result['correct'] == [True]*4
        assert 'code' not in result


def test_camera_loss_clears_current_digits(client, monkeypatch):
    fake = SyntheticCamera(main.game.config)
    monkeypatch.setattr(main,'camera',fake)
    post(client,'mode','camera')
    main.game.set_digits([4,None,None,None],[98,None,None,None])
    fake.stop()
    time.sleep(.15)
    assert client.get('/api/state').json()['digits'] == [None]*4
