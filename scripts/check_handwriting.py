"""Evaluate the real recognizer on held-out MNIST handwriting, not font images.

Run .venv/Scripts/python scripts/check_handwriting.py --download on first use.
No physical camera, server state, or room configuration is modified.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import sys
import time
import urllib.request

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.recognition import DigitRecognizer
from backend.digit_model import MODEL_NAME, MODEL_SHA256

DATA = ROOT / 'runtime' / 'mnist-eval'
OUTPUT = ROOT / 'runtime' / 'handwriting-test'
FILES = {
    'images.gz': ('t10k-images-idx3-ubyte.gz', '8d422c7b0a1c1c79245a5bcf07fe86e33eeafee792b84584aec276f5a2dbc4e6'),
    'labels.gz': ('t10k-labels-idx1-ubyte.gz', 'f7ae60f92e00ec6debd23a6088c31dbd2371eca3ffa0defaefb259924204aec6'),
}


def run(count=1000, download=False):
    DATA.mkdir(parents=True, exist_ok=True)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for name, (remote, digest) in FILES.items():
        path = DATA / name
        if not path.exists():
            if not download:
                raise RuntimeError('Test data missing; run again with --download')
            urllib.request.urlretrieve('https://storage.googleapis.com/cvdf-datasets/mnist/' + remote, path)
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise RuntimeError(f'Test data checksum mismatch: {name}')
    images = np.frombuffer(gzip.decompress((DATA / 'images.gz').read_bytes()), np.uint8, offset=16).reshape(-1,28,28)
    labels = np.frombuffer(gzip.decompress((DATA / 'labels.gz').read_bytes()), np.uint8, offset=8)
    recognizer = DigitRecognizer()
    results = []
    count = min(count, len(labels))
    for variant in ('normal', 'dim_rotated'):
        started = time.monotonic()
        correct = rejected = 0
        failures = []
        for i in range(count):
            image = cv2.resize(255-images[i], (168,168), interpolation=cv2.INTER_CUBIC)
            image = cv2.copyMakeBorder(image,45,45,45,45,cv2.BORDER_CONSTANT,value=255)
            if variant == 'dim_rotated':
                matrix = cv2.getRotationMatrix2D((129,129), 8, 1)
                image = cv2.warpAffine(image,matrix,(258,258),borderValue=255)
                image = (image.astype(np.float32)*.15+15).astype(np.uint8)
            observation = recognizer.recognize(image)
            correct += int(observation.digit == labels[i])
            rejected += int(observation.digit is None)
            if observation.digit != labels[i]:
                failures.append({'index': i, 'expected': int(labels[i]), 'detected': observation.digit,
                                 'score': observation.confidence, 'reason': observation.diagnostic['reason']})
        results.append({'variant': variant, 'count': count, 'correct': correct,
                        'rejected': rejected, 'wrong': count-correct-rejected,
                        'accuracy_percent': round(100*correct/count,2),
                        'seconds': round(time.monotonic()-started,3), 'failures': failures})
    sheet = Image.new('RGB',(1000,500),'#e6e9ec')
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype(str(ROOT/'backend/assets/DigitSans.ttf'),20)
    for digit in range(10):
        index = int(np.flatnonzero(labels == digit)[0])
        tile = Image.fromarray(255-images[index]).resize((168,168))
        x, y = (digit%5)*200+16, (digit//5)*250+16
        sheet.paste(tile,(x,y))
        obs = recognizer.recognize(np.array(tile))
        draw.text((x,y+180),f'{digit} -> {obs.digit} ({obs.confidence})',font=font,fill='black')
    sheet.save(OUTPUT/'samples.png')
    report = {'engine': MODEL_NAME, 'model_sha256': MODEL_SHA256,
              'dataset': 'MNIST held-out test set, first samples in original order',
              'note': 'Dataset accuracy is not a measurement of physical camera accuracy.',
              'results': results}
    (OUTPUT/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({**report,'results':[{k:v for k,v in r.items() if k!='failures'} for r in results]},indent=2))
    return all(r['accuracy_percent'] >= 90 for r in results)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--download', action='store_true')
    parser.add_argument('--count', type=int, default=1000)
    args = parser.parse_args()
    if not 1 <= args.count <= 10000:
        parser.error('--count must be between 1 and 10000')
    sys.exit(0 if run(args.count,args.download) else 1)
