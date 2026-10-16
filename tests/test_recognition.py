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
    assert result.confidence >= 15


@pytest.mark.parametrize('digit', range(10))
@pytest.mark.parametrize('angle', [-5, 0, 5])
def test_windows_arial_digits(recognizer, digit, angle):
    font_path = Path('C:/Windows/Fonts/arial.ttf')
    if not font_path.exists():
        pytest.skip('Windows Arial font not installed')
    image = Image.new('RGB', (260, 320), 'white')
    ImageDraw.Draw(image).text((130, 155), str(digit), anchor='mm',
                              font=ImageFont.truetype(str(font_path), 160), fill='black')
    image = image.rotate(angle, fillcolor='white')
    result = recognizer.recognize(cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR))
    assert result.digit == digit
    assert result.confidence >= 15


@pytest.mark.parametrize('kind', ['white', 'dark', 'blurred', 'two_digits', 'scribble'])
def test_ambiguous_blank_and_unreadable_input_rejected(recognizer, kind):
    if kind == 'white': image = np.full((320,260,3),255,np.uint8)
    elif kind == 'dark': image = np.zeros((320,260,3),np.uint8)
    elif kind == 'blurred': image = cv2.GaussianBlur(card(), (61,61), 20)
    elif kind == 'two_digits': image = card('42')
    else:
        image = np.full((320,260,3),255,np.uint8)
        cv2.line(image,(55,80),(200,210),(0,0,0),8)
        cv2.line(image,(200,80),(55,210),(0,0,0),8)
    assert recognizer.recognize(image).digit is None


def test_clipped_digit_is_not_misread_as_another_number(recognizer):
    result = recognizer.recognize(card()[:, 110:])
    assert result.digit is None
    assert 'reunaan' in result.diagnostic['reason']
    assert result.diagnostic['ocr_threshold'] == 15


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


def test_rejected_model_score_still_reaches_dashboard(monkeypatch):
    recognizer = DigitRecognizer()
    probabilities = np.full(10, .86/9, np.float32)
    probabilities[7] = .14
    monkeypatch.setattr(recognizer.model, 'predict', lambda image: probabilities)
    result = recognizer.recognize(card('7'), diagnostics=True)
    assert result.digit is None
    assert result.diagnostic['ocr_text'] == '7'
    assert result.diagnostic['ocr_confidence'] == 14
    assert result.diagnostic['ocr_threshold'] == 15
    assert result.diagnostic['input_image'].startswith('data:image/png;base64,')


@pytest.mark.parametrize('confidence', [15, 40])
def test_sensitive_model_reads_dark_image(monkeypatch, confidence):
    recognizer = DigitRecognizer()
    probabilities = np.full(10, (1-confidence/100)/9, np.float32)
    probabilities[4] = confidence/100
    monkeypatch.setattr(recognizer.model, 'predict', lambda image: probabilities)
    image = (card('4').astype(np.float32) * .08 + 12).astype(np.uint8)
    result = recognizer.recognize(image, diagnostics=True)
    assert result.digit == 4
    assert result.confidence == confidence
    assert result.diagnostic['engine'] == 'MNIST CNN (ONNX)'


def test_missing_model_does_not_create_observations(monkeypatch):
    monkeypatch.setattr('backend.recognition.recognizer_available', lambda: False)
    result = DigitRecognizer().recognize(card('4'), diagnostics=True)
    assert result.digit is None
    assert 'puuttuu' in result.diagnostic['reason']


def test_long_gap_requires_new_stabilization():
    s = Stabilizer()
    for t in [0,.35,.7]: s.update(Observation(2,95),t)
    assert s.stable == 2
    assert s.update(Observation(2,95), 3.0).digit is None
