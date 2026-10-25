"""Event cues for integrations; player browsers handle actual music playback."""
class AudioManager:
    def __init__(self, bus):
        self.cue = "idle"
        bus.subscribe(self.on_event)

    def on_event(self, event):
        cues = {"pregame.started": "calm", "timer.started": "tension", "timer.paused": "paused",
                "timer.warning": "urgency", "game.solved": "victory",
                "timer.expired": "timeout", "game.reset": "idle"}
        if event["type"] in cues:
            self.cue = cues[event["type"]]
