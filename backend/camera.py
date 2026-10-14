"""One native camera owner; capture thread is independent of expensive OCR."""
import platform
import threading
import time
import cv2


class CameraService:
    def __init__(self):
        self.thread = None
        self.stop_event = threading.Event()
        self.lock = threading.Lock()
        self.frame = None
        self.jpeg = None
        self.frame_at = 0.
        self.status = 'off'
        self.message = 'Kamera ei ole käytössä'

    def start(self, index=0):
        if self.thread and self.thread.is_alive():
            if self.stop_event.is_set():
                raise ValueError('Kamera sulkeutuu vielä. Yritä hetken kuluttua uudelleen.')
            return
        self.stop_event.clear()
        self.frame, self.jpeg, self.frame_at = None, None, 0.
        self.status, self.message = 'starting', 'Kameraa avataan…'
        self.thread = threading.Thread(target=self._capture, args=(index,), daemon=True, name='camera-capture')
        self.thread.start()

    def _capture(self, index):
        api = cv2.CAP_AVFOUNDATION if platform.system() == 'Darwin' else cv2.CAP_ANY
        cap = cv2.VideoCapture(index, api)
        try:
            if not cap.isOpened():
                self.status, self.message = 'error', 'Kameraa ei voitu avata. Tarkista kameran numero ja käyttöoikeus.'
                return
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            cap.set(cv2.CAP_PROP_FPS, 15)
            while not self.stop_event.is_set():
                ok, frame = cap.read()
                if not ok:
                    self.status, self.message = 'error', 'Kameran kuva katkesi. Käynnistä kamera uudelleen.'
                    break
                ok, encoded = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 78])
                with self.lock:
                    self.frame = frame
                    self.jpeg = encoded.tobytes() if ok else None
                    self.frame_at = time.monotonic()
                self.status, self.message = 'on', 'Kamera käytössä'
                self.stop_event.wait(.04)
        except Exception:
            self.status, self.message = 'error', 'Kameran lukeminen epäonnistui.'
        finally:
            cap.release()
            if self.stop_event.is_set():
                self.status, self.message = 'off', 'Kamera ei ole käytössä'
            with self.lock:
                self.frame, self.jpeg = None, None

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=3)
        self.status, self.message = 'off', 'Kamera ei ole käytössä'

    def latest(self):
        with self.lock:
            if self.frame is None or time.monotonic() - self.frame_at > 2:
                return None, self.frame_at
            return self.frame.copy(), self.frame_at

    def image(self):
        with self.lock:
            if time.monotonic() - self.frame_at > 2:
                return None
            return self.jpeg

    def info(self):
        with self.lock:
            shape = self.frame.shape if self.frame is not None else (720, 1280)
            stale = self.status == 'on' and time.monotonic() - self.frame_at > 2
            return {"status": 'error' if stale else self.status,
                    "message": 'Kamerakuva ei päivity. Käynnistä kamera uudelleen.' if stale else self.message,
                    "width": shape[1], "height": shape[0]}
