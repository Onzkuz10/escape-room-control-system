"""Verified, offline ONNX Model Zoo handwritten-digit CNN using OpenCV DNN."""
from functools import lru_cache
import hashlib
from pathlib import Path
import threading

import cv2
import numpy as np

MODEL_NAME = 'MNIST CNN (ONNX)'
MODEL_PATH = Path(__file__).parent / 'assets' / 'models' / 'mnist-12.onnx'
MODEL_SHA256 = '5c688690f8bacf667d4c2074af5ad0646ca328d7ab03eccf944a65b320171bdd'


@lru_cache(maxsize=1)
def recognizer_available() -> bool:
    try:
        return hashlib.sha256(MODEL_PATH.read_bytes()).hexdigest() == MODEL_SHA256
    except OSError:
        return False


class HandwrittenDigitModel:
    def __init__(self):
        self.local = threading.local()

    def predict(self, image: np.ndarray) -> np.ndarray:
        # OpenCV Net instances are mutable; each recognition worker owns its net.
        if not hasattr(self.local, 'net'):
            # Buffer loading also supports Windows project paths containing ä/ö.
            self.local.net = cv2.dnn.readNetFromONNX(np.frombuffer(MODEL_PATH.read_bytes(), dtype=np.uint8))
        self.local.net.setInput(image.astype(np.float32).reshape(1, 1, 28, 28) / 255.)
        logits = self.local.net.forward().reshape(10)
        exp = np.exp(logits - logits.max())
        return exp / exp.sum()
