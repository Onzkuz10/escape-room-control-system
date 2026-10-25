from typing import Literal
from pydantic import BaseModel, Field, model_validator


class Region(BaseModel):
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    width: float = Field(ge=0.04, le=1)
    height: float = Field(ge=0.08, le=1)

    @model_validator(mode="after")
    def within_frame(self):
        if self.x + self.width > 1.000001 or self.y + self.height > 1.000001:
            raise ValueError("Tunnistusalueen pitää olla kokonaan kuvassa.")
        return self


def default_regions():
    return [Region(x=0.085 + i * 0.225, y=0.25, width=0.155, height=0.5) for i in range(4)]


class Slide(BaseModel):
    title: str = Field(default="Uusi dia", max_length=120)
    body: str = Field(default="", max_length=2000)
    animation: Literal["fade", "float", "pulse", "none"] = "fade"
    layout: Literal["text", "seating", "movement", "code"] = "text"
    locked: bool = False
    media: str | None = Field(default=None, pattern=r"^/media/[a-f0-9]{32}\.(gif|mp4|webm|png|jpg|jpeg|webp)$")


class SoundChoice(BaseModel):
    name: str = Field(max_length=80)
    file: str = Field(pattern=r"^/media/[a-f0-9]{32}\.(mp3|wav|ogg|m4a)$")
    duration_seconds: float = Field(default=4, ge=.1, le=30)


class Presentation(BaseModel):
    slides: list[Slide] = Field(default_factory=lambda: [
        Slide(title="Tervetuloa pakohuoneeseen!", body="", animation="fade"),
        Slide(title="Istukaa pöytien ääreen.", body="Jakautukaa tasaisesti.", animation="none", layout="seating", locked=True),
        Slide(title="Seuratkaa valonauhaa.", body="", animation="none", layout="movement", locked=True),
        Slide(title="Ratkaiskaa koodi.", body="", layout="code"),
    ], min_length=1, max_length=20)
    pregame_music: str | None = Field(default=None, pattern=r"^/media/[a-f0-9]{32}\.(mp3|wav|ogg|m4a)$")
    game_music: str | None = Field(default=None, pattern=r"^/media/[a-f0-9]{32}\.(mp3|wav|ogg|m4a)$")
    victory_video: str | None = Field(default=None, pattern=r"^/media/[a-f0-9]{32}\.(mp4|webm)$")
    defeat_video: str | None = Field(default=None, pattern=r"^/media/[a-f0-9]{32}\.(mp4|webm)$")
    victory_sounds: list[SoundChoice] = Field(default_factory=list, max_length=4)
    victory_sound: str | None = Field(default=None, pattern=r"^/media/[a-f0-9]{32}\.(mp3|wav|ogg|m4a)$")
    volume: float = Field(default=0.35, ge=0, le=1)
    muted: bool = False

    @model_validator(mode='after')
    def fixed_intro_sequence(self):
        if self.victory_sound and self.victory_sound not in [choice.file for choice in self.victory_sounds]:
            raise ValueError('Valitse lopetusääni tallennetuista vaihtoehdoista.')
        locked_indices = [index for index, slide in enumerate(self.slides) if slide.locked]
        if locked_indices:
            if len(locked_indices) != 2 or locked_indices[1] != locked_indices[0] + 1:
                raise ValueError('Lukitut pöytä- ja valonauhaohjeet on säilytettävä peräkkäisinä dioina.')
            pair = [self.slides[index] for index in locked_indices]
            if [slide.layout for slide in pair] != ['seating', 'movement']:
                raise ValueError('Lukittu pöytäohje tulee aina ennen valonauhaohjetta.')
            if any(slide.media or slide.animation != 'none' for slide in pair):
                raise ValueError('Lukittujen ohjediojen animaatio on kiinteä eikä niiden mediaa voi vaihtaa.')
        return self


class Config(BaseModel):
    code: str = Field(default="4279", pattern=r"^[0-9]{4}$")
    duration_seconds: int = Field(default=3600, ge=1, le=14400)
    regions: list[Region] = Field(default_factory=default_regions, min_length=4, max_length=4)
    camera_index: int = Field(default=0, ge=0)
    require_human_approval: bool = False
    presentation: Presentation = Field(default_factory=Presentation)


class Command(BaseModel):
    action: Literal["start", "pregame", "next_slide", "previous_slide", "next_view", "previous_view", "presentation", "game_settings", "audio_settings", "victory_sound", "pause", "reset", "simulate", "approve_solution", "require_human_approval", "mode", "digits", "digit", "code", "duration", "regions", "camera_start", "camera_stop"]
    value: object = None
