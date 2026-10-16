"""Authoritative game state. Only the asyncio server thread mutates this object."""
import time
from .models import Config


class GameState:
    def __init__(self, config: Config, bus, clock=time.monotonic):
        self.config, self.bus, self.clock = config, bus, clock
        self.mode = "manual"
        self.digits = [None] * 4
        self.confidences = [None] * 4
        self.remaining = float(config.duration_seconds)
        self.running = False
        self.phase = "ready"
        self.last_tick = clock()
        self.warning_sent = False
        self.generation = 0
        self.recognition_diagnostics = [None] * 4
        self.recognition_at = None
        self.camera = {"status": "off", "message": "Kamera ei ole käytössä", "width": 1280, "height": 720,
                       "ocr_available": False}
        bus.emit("system.ready")

    def tick(self):
        now = self.clock()
        if self.running:
            previous = self.remaining
            self.remaining = max(0., self.remaining - (now - self.last_tick))
            if previous > 300 >= self.remaining and not self.warning_sent:
                self.warning_sent = True
                self.bus.emit("timer.warning", remaining=round(self.remaining))
            if self.remaining <= 0:
                self.running = False
                self.phase = "expired"
                self.bus.emit("timer.expired")
        self.last_tick = now

    def start(self):
        self.tick()
        if self.phase in ("solved", "expired"):
            raise ValueError("Nollaa huone ennen uuden pelin käynnistämistä.")
        if not self.running:
            self.running, self.phase = True, "running"
            self.bus.emit("timer.started")

    def pause(self):
        self.tick()
        if self.running:
            self.running, self.phase = False, "paused"
            self.bus.emit("timer.paused")

    def reset(self):
        self.running, self.phase = False, "ready"
        self.remaining = float(self.config.duration_seconds)
        self.last_tick = self.clock()
        self.digits, self.confidences = [None] * 4, [None] * 4
        self.warning_sent = False
        self.generation += 1
        self.recognition_diagnostics, self.recognition_at = [None] * 4, None
        self.bus.emit("game.reset")

    def set_digits(self, digits, confidences=None, *, allow_solve=True):
        self.tick()  # Expiry wins if the deadline has already passed.
        if self.phase in ("solved", "expired"):
            return
        new_conf = confidences or [None] * 4
        if self.digits != digits:
            self.digits = list(digits)
            self.bus.emit("digits.changed", digits=self.digits, correct=self.correct())
        self.confidences = new_conf
        if allow_solve and all(self.correct()):
            self.running, self.phase = False, "solved"
            self.bus.emit("game.solved", remaining=round(self.remaining, 2))

    def clear_detection(self):
        self.generation += 1
        self.digits, self.confidences = [None] * 4, [None] * 4
        self.recognition_diagnostics, self.recognition_at = [None] * 4, None

    def correct(self):
        return [digit is not None and str(digit) == self.config.code[i] for i, digit in enumerate(self.digits)]

    def snapshot(self, player=False):
        result = {"mode": self.mode, "digits": self.digits, "correct": self.correct(),
                  "remaining_seconds": self.remaining, "duration_seconds": self.config.duration_seconds,
                  "running": self.running, "phase": self.phase, "server_time": time.time()}
        if not player:
            result.update(code=self.config.code, regions=[r.model_dump() for r in self.config.regions],
                          confidences=self.confidences, camera=self.camera,
                          recognition_diagnostics=self.recognition_diagnostics, recognition_at=self.recognition_at,
                          camera_index=self.config.camera_index, events=list(self.bus.history))
        return result
