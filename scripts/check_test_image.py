"""Generate independent font fixtures and run the real camera recognition loop.

Run from the project root with .venv/Scripts/python scripts/check_test_image.py.
The live server and physical camera are not used by this isolated process.
"""
import json
from pathlib import Path
import sys
import time

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend import main
from backend.events import EventBus
from backend.models import Config
from backend.digit_model import recognizer_available
from backend.state import GameState

OUTPUT = ROOT / 'runtime' / 'ocr-test'
OUTPUT.mkdir(parents=True, exist_ok=True)
FONT = Path('C:/Windows/Fonts/arial.ttf')
CONFIG = Config(code='4279')


def create_image(digits, filename):
    image = Image.new('RGB', (1280, 720), '#e6e9ec')
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(str(FONT), 170)
    for region, digit in zip(CONFIG.regions, digits):
        left, top = round(region.x * 1280), round(region.y * 720)
        right = round((region.x + region.width) * 1280)
        bottom = round((region.y + region.height) * 720)
        draw.rounded_rectangle((left - 12, top - 12, right + 12, bottom + 12), radius=8, fill='white')
        if digit is not None:
            box = draw.textbbox((0, 0), str(digit), font=font)
            x = (left + right - (box[2] - box[0])) / 2 - box[0]
            y = (top + bottom - (box[3] - box[1])) / 2 - box[1]
            draw.text((x, y), str(digit), font=font, fill='black')
    path = OUTPUT / filename
    image.save(path)
    return path


class ImageCamera:
    def __init__(self, path):
        self.frame = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
        if self.frame is None:
            raise RuntimeError(f'Cannot load {path}')
        self.status = 'on'

    def latest(self):
        return self.frame.copy(), time.monotonic()

    def info(self):
        return {'status': self.status, 'message': 'Test image', 'width': 1280,
                'height': 720, 'ocr_available': recognizer_available()}

    def stop(self):
        self.status = 'off'


def check_image(path, expected):
    main.bus = EventBus()
    main.game = GameState(CONFIG, main.bus)
    main.camera = ImageCamera(path)
    main.clients.clear()
    with TestClient(main.app) as client:
        client.post('/api/command', json={'action': 'mode', 'value': 'camera'}).raise_for_status()
        deadline = time.monotonic() + (2 if expected == [None] * 4 else 6)
        while True:
            state = client.get('/api/state').json()
            if (expected != [None] * 4 and state['digits'] == expected) or time.monotonic() >= deadline:
                break
            time.sleep(.1)
        player_state = main.game.snapshot(player=True)
    expected_phase = 'solved' if expected == [4, 2, 7, 9] else 'ready'
    passed = (state['digits'] == expected and state['phase'] == expected_phase
              and player_state['digits'] == expected)
    return {'image': str(path), 'expected': expected, 'detected': state['digits'],
            'confidence': state['confidences'], 'correct': state['correct'],
            'phase': state['phase'], 'player_digits': player_state['digits'], 'passed': passed}


if __name__ == '__main__':
    results = []
    for digits, name in [([4, 2, 7, 9], 'digits-4279.png'),
                         ([4, 2, 7, 8], 'digits-4278.png'),
                         ([0, 3, 5, 6], 'digits-0356.png'),
                         ([1, 6, 8, 0], 'digits-1680.png'),
                         ([None] * 4, 'blank.png')]:
        path = create_image(digits, name)
        results.append(check_image(path, digits))
    report = {'font': str(FONT), 'ocr_available': recognizer_available(), 'results': results}
    (OUTPUT / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
    sys.exit(0 if all(result['passed'] for result in results) else 1)
