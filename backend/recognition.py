"""Local handwritten digit recognition with a pretrained MNIST CNN."""
import base64
from dataclasses import dataclass
import cv2
import numpy as np
from .digit_model import HandwrittenDigitModel, MODEL_NAME, recognizer_available


@dataclass(frozen=True)
class Observation:
    digit: int | None = None
    confidence: float | None = None
    diagnostic: dict | None = None


class DigitRecognizer:
    def __init__(self):
        self.model = HandwrittenDigitModel()

    @staticmethod
    def prepare(roi):
        """Extract one glyph, fit it into 20x20, and center it in a 28x28 input."""
        if roi.size == 0 or min(roi.shape[:2]) < 4:
            return None, 'Rajaus on tyhjä tai liian pieni'
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY) if roi.ndim == 3 else roi
        if float(gray.max()) - float(gray.min()) < 3:
            return None, 'Alue on tasainen; ei luettavaa numeroa'
        gray = cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX)
        smooth = cv2.GaussianBlur(gray, (3, 3), 0)
        _, mask = cv2.threshold(smooth, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        border = np.concatenate((mask[0], mask[-1], mask[:, 0], mask[:, -1]))
        if np.mean(border) > 127:
            mask = 255 - mask
            foreground = gray
        else:
            foreground = 255 - gray
        count, labels, stats, _ = cv2.connectedComponentsWithStats(mask)
        candidates = []
        for i in range(1, count):
            x, y, w, h, area = stats[i]
            if area < max(5, mask.size * .0003) or h < 5:
                continue
            if area > mask.size * .65:
                continue
            if (x == 0 or y == 0 or x+w == gray.shape[1] or y+h == gray.shape[0]) and (w > gray.shape[1]*.8 or h > gray.shape[0]*.8):
                continue
            candidates.append(i)
        if not candidates:
            return None, 'Alueelta ei löytynyt erottuvaa numeroa'
        candidates.sort(key=lambda i: stats[i, cv2.CC_STAT_AREA], reverse=True)
        primary = candidates[0]
        x, y, w, h, area = stats[primary]
        selected = [primary]
        for i in candidates[1:]:
            xx, yy, ww, hh, aa = stats[i]
            if aa < area * .15:
                continue
            overlap = min(x+w, xx+ww) - max(x, xx)
            if overlap < min(w, ww)*.15:
                return None, 'Alueella on useita merkkejä; rajaa yksi numero'
            selected.append(i)
        ys, xs = np.where(np.isin(labels, selected))
        x, y, right, bottom = xs.min(), ys.min(), xs.max()+1, ys.max()+1
        rejection = None
        if min(x, y) < 2 or right > gray.shape[1]-2 or bottom > gray.shape[0]-2:
            rejection = 'Numero leikkautuu rajauksen reunaan; suurenna rajausta'
        # A pair of long, crossing diagonals is a common non-digit distractor.
        lines = cv2.HoughLinesP(mask[y:bottom, x:right], 1, np.pi/180,
                                threshold=max(10, int(max(right-x, bottom-y)*.4)),
                                minLineLength=max(right-x, bottom-y)*.65, maxLineGap=4)
        diagonal_directions = set()
        if lines is not None:
            for x1, y1, x2, y2 in lines[:, 0]:
                dx, dy = int(x2-x1), int(y2-y1)
                if dx and .6 < abs(dy/dx) < 1.8:
                    diagonal_directions.add(1 if dy/dx > 0 else -1)
        if len(diagonal_directions) == 2:
            rejection = 'Alueella on risteäviä viivoja numeron sijaan'
        glyph = foreground[y:bottom, x:right].copy()
        support = np.isin(labels[y:bottom, x:right], selected).astype(np.uint8)
        support = cv2.dilate(support, np.ones((3,3), np.uint8))
        glyph[support == 0] = 0
        height, width = glyph.shape
        scale = 20 / max(height, width)
        glyph = cv2.resize(glyph, (max(1, round(width*scale)), max(1, round(height*scale))), interpolation=cv2.INTER_AREA)
        canvas = np.zeros((28,28), np.uint8)
        gh, gw = glyph.shape
        canvas[(28-gh)//2:(28-gh)//2+gh, (28-gw)//2:(28-gw)//2+gw] = glyph
        moments = cv2.moments(canvas)
        if moments['m00']:
            dx = 13.5 - moments['m10']/moments['m00']
            dy = 13.5 - moments['m01']/moments['m00']
            canvas = cv2.warpAffine(canvas, np.float32([[1,0,dx],[0,1,dy]]), (28,28))
        return canvas, rejection

    def recognize(self, roi: np.ndarray, *, diagnostics=False) -> Observation:
        details = {'engine': MODEL_NAME, 'ocr_text': None, 'ocr_confidence': None,
                   'ocr_threshold': 15, 'shape_digit': None, 'shape_confidence': None,
                   'input_image': None, 'roi_image': None, 'alternatives': []}
        def result(reason, digit=None, confidence=None):
            return Observation(digit, confidence, {**details, 'reason': reason})
        if diagnostics and roi.size and min(roi.shape[:2]) > 0:
            scale = min(1., 220 / max(roi.shape[:2]))
            preview = cv2.resize(roi, (max(1, round(roi.shape[1]*scale)), max(1, round(roi.shape[0]*scale))), interpolation=cv2.INTER_AREA)
            ok, encoded = cv2.imencode('.jpg', preview, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if ok:
                details['roi_image'] = 'data:image/jpeg;base64,' + base64.b64encode(encoded).decode('ascii')
        if not recognizer_available():
            return result('Käsialamalli puuttuu tai on vioittunut')
        image, rejection = self.prepare(roi)
        if image is None:
            return result(rejection)
        if diagnostics:
            ok, encoded = cv2.imencode('.png', image)
            if ok:
                details['input_image'] = 'data:image/png;base64,' + base64.b64encode(encoded).decode('ascii')
        try:
            probabilities = self.model.predict(image)
        except cv2.error:
            return result('Käsialamallin suoritus epäonnistui')
        order = np.argsort(probabilities)[::-1]
        best = int(order[0])
        confidence = round(float(probabilities[best])*100, 1)
        details.update(ocr_text=str(best), ocr_confidence=confidence,
                       alternatives=[{'digit': int(i), 'score': round(float(probabilities[i])*100, 1)} for i in order[:3]])
        if confidence < 15:
            return result('Mallin pistemäärä jää 15 pisteen alle')
        if rejection:
            return result(rejection)
        if float(probabilities[order[0]] - probabilities[order[1]]) < .05:
            return result('Mallin kaksi parasta ehdotusta ovat liian lähellä toisiaan')
        return result('Käsialamallin havainto; odottaa ajallista vakautusta', best, confidence)


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
