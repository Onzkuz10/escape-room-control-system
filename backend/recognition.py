"""Offline OCR with geometric rejection and time-based stabilization."""
from dataclasses import dataclass
import cv2
import numpy as np
import pytesseract
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


@dataclass(frozen=True)
class Observation:
    digit: int | None = None
    confidence: float | None = None


class DigitRecognizer:
    def __init__(self):
        self.templates = []
        assets = Path(__file__).parent / 'assets'
        fonts = [ImageFont.truetype(str(assets / name), 160) for name in ('DigitSans.ttf', 'DigitSans-Bold.ttf')]
        for digit in range(10):
            glyphs = []
            for font in fonts:
                image = Image.new('L', (260, 320), 0)
                ImageDraw.Draw(image).text((130, 155), str(digit), anchor='mm', font=font, fill=255)
                glyphs.append(np.array(image))
            for font in (cv2.FONT_HERSHEY_SIMPLEX, cv2.FONT_HERSHEY_DUPLEX):
                for thickness in (4, 8):
                    image = np.zeros((240, 200), np.uint8)
                    cv2.putText(image, str(digit), (30, 180), font, 5, 255, thickness, cv2.LINE_AA)
                    glyphs.append(image)
            templates = []
            for glyph in glyphs:
                for angle in (-6, 0, 6):
                    matrix = cv2.getRotationMatrix2D((glyph.shape[1]/2, glyph.shape[0]/2), angle, 1)
                    rotated = cv2.warpAffine(glyph, matrix, (glyph.shape[1], glyph.shape[0]))
                    templates.append(self.normalize(rotated))
            self.templates.append(templates)

    @staticmethod
    def normalize(ink):
        points = cv2.findNonZero((ink > 100).astype(np.uint8))
        if points is None:
            return np.zeros((64, 64), np.float32)
        x, y, w, h = cv2.boundingRect(points)
        scale = 54 / max(h, w)
        mask = cv2.resize(ink[y:y+h, x:x+w], (max(1, round(w*scale)), max(1, round(h*scale))), interpolation=cv2.INTER_AREA)
        canvas = np.zeros((64, 64), np.float32)
        mh, mw = mask.shape
        canvas[(64-mh)//2:(64-mh)//2+mh, (64-mw)//2:(64-mw)//2+mw] = mask / 255.
        return canvas

    def match(self, ink):
        mask = self.normalize(ink)
        scores = [max(float(2 * np.minimum(mask, template).sum() / (mask.sum() + template.sum() + 1e-6)) for template in variants) for variants in self.templates]
        order = sorted(range(10), key=lambda i: scores[i], reverse=True)
        best = order[0]
        return best, scores[best], scores[best] - scores[order[1]]

    def recognize(self, roi: np.ndarray) -> Observation:
        if roi.size == 0 or min(roi.shape[:2]) < 40:
            return Observation()
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY) if roi.ndim == 3 else roi
        if gray.mean() < 85 or cv2.Laplacian(gray, cv2.CV_64F).var() < 20:
            return Observation()
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        _, ink = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        coverage = np.count_nonzero(ink) / ink.size
        if not .006 < coverage < .40:
            return Observation()
        contours, _ = cv2.findContours(ink, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)
        if not contours:
            return Observation()
        area = cv2.contourArea(contours[0])
        if area < 50:
            return Observation()
        # More than one substantial glyph is not a single digit.
        if any(cv2.contourArea(c) > max(25, area * .12) for c in contours[1:]):
            return Observation()
        x, y, w, h = cv2.boundingRect(contours[0])
        height, width = gray.shape
        if h < height * .20 or not .07 < w / h < 1.15:
            return Observation()
        # A clipped glyph (or paper edge) must never become an accepted digit.
        if min(x, y) < 3 or x + w > width - 3 or y + h > height - 3:
            return Observation()
        best, score, margin = self.match(ink[y:y+h, x:x+w])
        # A very strong shape match is useful for isolated digits OCR calls letters.
        # This does not consult the room's target code.
        if score >= .84 and margin >= .085:
            return Observation(best, round(score * 100, 1))
        if score < .68 or margin < .035:
            return Observation()
        glyph = 255 - ink[y:y+h, x:x+w]
        target_h = 180
        glyph = cv2.resize(glyph, (max(12, round(w * target_h / h)), target_h), interpolation=cv2.INTER_CUBIC)
        glyph = cv2.copyMakeBorder(glyph, 35, 35, 45, 45, cv2.BORDER_CONSTANT, value=255)
        try:
            data = pytesseract.image_to_data(glyph, config="--psm 13 --oem 3 -c tessedit_char_whitelist=0123456789", output_type=pytesseract.Output.DICT, timeout=2)
        except (RuntimeError, pytesseract.TesseractError):
            return Observation()
        tokens = [(t.strip(), float(c)) for t, c in zip(data['text'], data['conf']) if t.strip()]
        if len(tokens) != 1:
            return Observation()
        text, confidence = tokens[0]
        if len(text) != 1 or text not in '0123456789' or confidence < 75 or int(text) != best:
            return Observation()
        return Observation(best, round(min(confidence, score * 100), 1))


class Stabilizer:
    """3 identical samples across >= .65 s; bad signal clears within .55 s.

    Fresh observations are required after a long gap. No majority vote can retain
    an old correct digit through a new contradictory observation.
    """
    def __init__(self):
        self.candidate = None
        self.count = 0
        self.since = 0.
        self.last_valid = -100.
        self.stable = None
        self.confidence = None

    def update(self, observation: Observation, now: float) -> Observation:
        digit = observation.digit
        if digit is None:
            self.candidate, self.count = None, 0
            if now - self.last_valid >= .55:
                self.stable, self.confidence = None, None
        else:
            if digit != self.candidate or now - self.last_valid > 1.5:
                self.candidate, self.count, self.since = digit, 1, now
                # Immediately remove a previously stable contradictory digit.
                if digit != self.stable or now - self.last_valid > 1.5:
                    self.stable, self.confidence = None, None
            else:
                self.count += 1
            self.last_valid = now
            if self.count >= 3 and now - self.since >= .65:
                self.stable, self.confidence = digit, observation.confidence
        return Observation(self.stable, self.confidence)
