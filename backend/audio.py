"""Extension boundary for future music. V1 never plays or loads audio."""
class AudioManager:
    def __init__(self, bus):
        self.cue = "idle"
        bus.subscribe(self.on_event)

    def on_event(self, event):
        cues = {"timer.started": "tension", "timer.paused": "paused",
                "timer.warning": "urgency", "game.solved": "victory",
                "timer.expired": "timeout", "game.reset": "idle"}
        if event["type"] in cues:
            self.cue = cues[event["type"]]
        # Future adapter: queue a command to a local audio engine here.
        # Do not perform blocking playback inside the event bus.
