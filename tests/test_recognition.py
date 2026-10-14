from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import pytest
from backend.recognition import DigitRecognizer, Observation, Stabilizer

FONT = Path(__file__).resolve().parents[1] / 'backend/assets/DigitSans.ttf'


def card(text='4', rotation=0):
    image = Image.new('RGB', (260, 320), 'white')
    ImageDraw.Draw(image).text((130, 155), text, anchor='mm', font=ImageFont.truetype(str(FONT), 160), fill='black')
    if rotation:
        image = image.rotate(rotation, fillcolor='white')
    return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)


@pytest.fixture(scope='module')
def recognizer():
    return DigitRecognizer()


@pytest.mark.parametrize('digit', range(10))
@pytest.mark.parametrize('angle', [-5, 0, 5])
def test_all_printed_digits_and_small_rotation(recognizer, digit, angle):
    result = recognizer.recognize(card(str(digit), angle))
    assert result.digit == digit
    assert result.confidence >= 75


@pytest.mark.parametrize('kind', ['white', 'dark', 'blurred', 'two_digits', 'clipped', 'scribble'])
def test_ambiguous_blank_and_unreadable_input_rejected(recognizer, kind):
    if kind == 'white': image = np.full((320,260,3),255,np.uint8)
    elif kind == 'dark': image = np.zeros((320,260,3),np.uint8)
    elif kind == 'blurred': image = cv2.GaussianBlur(card(), (61,61), 20)
    elif kind == 'two_digits': image = card('42')
    elif kind == 'clipped': image = card()[:,110:]
    else:
        image = np.full((320,260,3),255,np.uint8)
        cv2.line(image,(55,80),(200,210),(0,0,0),8)
        cv2.line(image,(200,80),(55,210),(0,0,0),8)
    assert recognizer.recognize(image).digit is None


def test_temporal_stability_and_signal_loss():
    s = Stabilizer()
    assert s.update(Observation(4,95), 0).digit is None
    assert s.update(Observation(4,95), .3).digit is None
    assert s.update(Observation(4,95), .7).digit == 4
    assert s.update(Observation(), .9).digit == 4
    assert s.update(Observation(), 1.3).digit is None
    assert s.update(Observation(4,95), 1.5).digit is None
    assert s.update(Observation(4,95), 1.9).digit is None
    assert s.update(Observation(4,95), 2.2).digit == 4
    assert s.update(Observation(7,95), 2.3).digit is None


def test_long_gap_requires_new_stabilization():
    s = Stabilizer()
    for t in [0,.35,.7]: s.update(Observation(2,95),t)
    assert s.stable == 2
    assert s.update(Observation(2,95), 3.0).digit is None
