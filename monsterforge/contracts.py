"""Contracts required by the modular character constructor."""
from __future__ import annotations
import json
from hashlib import sha256
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from .paths import HUMANOID_CONTRACT_PATH, STYLE_PATH


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Rect(StrictModel):
    x: float = Field(ge=0.0, le=1.0)
    y: float = Field(ge=0.0, le=1.0)
    width: float = Field(gt=0.0, le=1.0)
    height: float = Field(gt=0.0, le=1.0)

    @model_validator(mode="after")
    def inside_canvas(self) -> "Rect":
        if self.x + self.width > 1.0 or self.y + self.height > 1.0:
            raise ValueError("template rectangle leaves the canvas")
        return self


class TemplatePanel(StrictModel):
    view: Literal["front", "isometric"]
    rect: Rect


class HumanoidSlot(StrictModel):
    id: Literal[
        "head",
        "torso",
        "left_arm",
        "right_arm",
        "left_leg",
        "right_leg",
        "back_attachment",
    ]
    label: str
    required: bool = True
    allowed_bones: list[str]
    front_rect: Rect


class HumanoidTemplateContract(StrictModel):
    schema_version: int = 1
    id: Literal["humanoid_v1"]
    source_image: str
    panels: list[TemplatePanel]
    slots: list[HumanoidSlot]

    @model_validator(mode="after")
    def unique_slots_and_views(self) -> "HumanoidTemplateContract":
        if len({slot.id for slot in self.slots}) != len(self.slots):
            raise ValueError("humanoid slot ids must be unique")
        if len(self.panels) != 1 or self.panels[0].view != "front":
            raise ValueError("humanoid template needs one Front positioning sheet")
        expected = {"head", "torso", "left_arm", "right_arm", "left_leg", "right_leg", "back_attachment"}
        if {slot.id for slot in self.slots} != expected:
            raise ValueError("humanoid template must contain the complete seven-part constructor")
        _validate_non_overlapping([slot.front_rect for slot in self.slots])
        return self


def _validate_non_overlapping(rectangles: list[Rect]) -> None:
    for index, left in enumerate(rectangles):
        for right in rectangles[index + 1 :]:
            overlaps_x = left.x < right.x + right.width and right.x < left.x + left.width
            overlaps_y = left.y < right.y + right.height and right.y < left.y + left.height
            if overlaps_x and overlaps_y:
                raise ValueError("positioning slots must not overlap")


class StyleProfile(StrictModel):
    name: str
    art_direction: str
    geometry_rules: str
    material_rules: str
    presentation_rules: str
    global_negative: str


def file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def load_humanoid_contract() -> HumanoidTemplateContract:
    return HumanoidTemplateContract.model_validate(_load(HUMANOID_CONTRACT_PATH))


def load_style_profile() -> StyleProfile:
    return StyleProfile.model_validate(_load(STYLE_PATH))
