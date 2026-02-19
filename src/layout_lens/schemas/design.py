from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from .base import StrictModel


ShortText = Annotated[str, Field(min_length=1, max_length=100)]
OneLine = Annotated[str, Field(min_length=1, max_length=500)]


class DesignElement(StrictModel):
    label: ShortText = Field(
        description="Plain-English item name/type (e.g. 'bed', 'desk', 'bookshelf'). These should only be tangible items. These should NOT be rooms, zones, or spaces.",
    )
    quantity: int = Field(
        default=1,
        ge=1,
        le=12,
        description="How many of this item to include.",
    )


class Design(StrictModel):
    style_tags: list[ShortText] = Field(
        default_factory=list,
        min_length=4,
        max_length=8,
        description="Short style keywords (e.g. 'cozy', 'minimal', 'playful').",
    )

    color_palette: list[ShortText] = Field(
        default_factory=list,
        min_length=4,
        max_length=8,
        description="A few color words/phrases that define the room (e.g. 'warm white', 'sky blue').",
    )

    lighting_mood: list[ShortText] = Field(
        default_factory=list,
        min_length=2,
        max_length=4,
        description="Lighting intent keywords (e.g. 'soft ambient', 'task lighting at desk').",
    )

    zones: list[ShortText] = Field(
        default_factory=list,
        max_length=10,
        description="Optional sub-areas inside the space (non-geometric)."
    )

    required_elements: list[DesignElement] = Field(
        default_factory=list,
        max_length=6,
        description="Items explicitly required by the user request. These should only be tangible items. These should NOT be rooms, areas, zones, or spaces.",
    )

    recommended_elements: list[DesignElement] = Field(
        default_factory=list,
        min_length=1,
        max_length=5,
        description="Helpful additions beyond must-haves (e.g. lamps, fans, pantings, rugs, etc.). These should only be tangible items. These should NOT be rooms, areas, zones, or spaces.",
    )

    layout_preferences: list[OneLine] = Field(
        default_factory=list,
        min_length=1,
        max_length=10,
        description="High-level layout preferences (e.g. 'desk near window', 'clear path from door').",
    )

    summary: OneLine = Field(
        default="",
        description="1-2 sentence human-readable summary of the design intent.",
    )
