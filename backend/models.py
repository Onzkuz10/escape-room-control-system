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


class Config(BaseModel):
    code: str = Field(default="4279", pattern=r"^[0-9]{4}$")
    duration_seconds: int = Field(default=3600, ge=1, le=14400)
    regions: list[Region] = Field(default_factory=default_regions, min_length=4, max_length=4)
    camera_index: int = Field(default=0, ge=0, le=9)


class Command(BaseModel):
    action: Literal["start", "pause", "reset", "simulate", "mode", "digits", "digit", "code", "duration", "regions", "camera_start", "camera_stop"]
    value: object = None
