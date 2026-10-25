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
        self.slide_index = 0
        self.game_view = "timer"
        self.result_video_playing = False
        self.result_at = None
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
                self.result_at = time.time()
                self.bus.emit("timer.expired")
        self.last_tick = now

    def pregame(self):
        if self.phase != "ready":
            raise ValueError("Pre-game voidaan aloittaa valmiustilasta. Nollaa huone uutta peliä varten.")
        self.phase, self.slide_index = "pregame", 0
        self.clear_detection()
        self.bus.emit("pregame.started")

    def change_slide(self, step):
        if self.phase != "pregame":
            raise ValueError("Dioja voi vaihtaa vain pre-game-vaiheessa.")
        self.slide_index = max(0, min(len(self.config.presentation.slides) - 1, self.slide_index + step))
        self.bus.emit("pregame.slide", index=self.slide_index)

    def start(self):
        self.tick()
        if self.phase in ("solved", "expired"):
            raise ValueError("Nollaa huone ennen uuden pelin käynnistämistä.")
        if not self.running:
            if self.phase == "pregame":
                self.clear_detection()
            self.running, self.phase = True, "running"
            self.bus.emit("timer.started")

    def next_view(self):
        if self.phase in ("solved", "expired"):
            video = self.config.presentation.victory_video if self.phase == "solved" else self.config.presentation.defeat_video
            if not video:
                raise ValueError("Lopetusvideota ei ole valittu. Lisää video ennen seuraavaa peliä.")
            self.result_video_playing = True
            self.bus.emit("game.view", view="result_video")
            return
        self.change_view("digits" if self.game_view == "timer" else "timer")

    def previous_view(self):
        if self.phase in ("solved", "expired"):
            self.result_video_playing = False
            self.bus.emit("game.view", view="result")
            return
        self.change_view("timer")

    def change_view(self, view):
        self.tick()
        if self.phase not in ("running", "paused"):
            raise ValueError("Näkymää voi vaihtaa pelin aikana.")
        self.game_view = view
        self.bus.emit("game.view", view=self.game_view)
        if self.mode == "manual":
            self.set_digits(self.digits)

    def pause(self):
        self.tick()
        if self.running:
            self.running, self.phase = False, "paused"
            self.bus.emit("timer.paused")

    def reset(self):
        self.running, self.phase = False, "ready"
        self.slide_index = 0
        self.game_view = "timer"
        self.result_video_playing = False
        self.result_at = None
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
        if allow_solve and not self.config.require_human_approval and self.phase in ("running", "paused") and self.game_view == "digits" and all(self.correct()):
            self.running, self.phase = False, "solved"
            self.result_at = time.time()
            self.bus.emit("game.solved", remaining=round(self.remaining, 2))

    def approve_solution(self):
        self.tick()
        if self.phase not in ("running", "paused"):
            raise ValueError("Ratkaisun voi hyväksyä vain käynnissä olevassa tai pysäytetyssä pelissä.")
        self.running, self.phase = False, "solved"
        self.result_at = time.time()
        self.bus.emit("game.solved", remaining=round(self.remaining, 2), approved_by_operator=True)

    def clear_detection(self):
        self.generation += 1
        self.digits, self.confidences = [None] * 4, [None] * 4
        self.recognition_diagnostics, self.recognition_at = [None] * 4, None

    def correct(self):
        return [digit is not None and str(digit) == self.config.code[i] for i, digit in enumerate(self.digits)]

    def snapshot(self, player=False):
        visible_correct = self.correct() if not player or self.phase == "solved" else [False] * 4
        result = {"mode": self.mode, "digits": self.digits, "correct": visible_correct,
                  "remaining_seconds": self.remaining, "duration_seconds": self.config.duration_seconds,
                  "running": self.running, "phase": self.phase, "server_time": time.time(),
                  "slide_index": self.slide_index, "game_view": self.game_view,
                  "result_video_playing": self.result_video_playing,
                  "result_at": self.result_at,
                  "solution_digits": [int(d) for d in self.config.code] if self.phase == "solved" else None,
                  "presentation": self.config.presentation.model_dump()}
        if not player:
            result.update(code=self.config.code, regions=[r.model_dump() for r in self.config.regions],
                          confidences=self.confidences, camera=self.camera,
                          recognition_diagnostics=self.recognition_diagnostics, recognition_at=self.recognition_at,
                          camera_index=self.config.camera_index, events=list(self.bus.history))
            result['require_human_approval'] = self.config.require_human_approval
        return result
