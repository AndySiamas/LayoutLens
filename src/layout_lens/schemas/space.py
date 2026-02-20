from __future__ import annotations
from typing import Literal
from enum import Enum

from pydantic import Field, field_validator

from .base import StrictModel


class Point2D(StrictModel):
    """2D point in meters in local room coordinates."""
    x: float = Field(description="X coordinate in meters.")
    y: float = Field(description="Y coordinate in meters.")


class OpeningKind(str, Enum):
    """High-level category for a boundary opening."""
    DOOR = "door"
    WINDOW = "window"
    OTHER = "other"


class Opening(StrictModel):
    """
    A door/window/opening anchored to a specific boundary edge.

    The opening is defined along the edge from boundary[edge_index] to boundary[edge_index + 1],
    where `center` is a normalized 0..1 parameter representing the opening's center position
    along that edge.
    """
    kind: OpeningKind = Field(description="Type of opening.")
    edge_index: int = Field(
        ge=0,
        description="Index of the boundary edge (edge i is boundary[i] -> boundary[i+1], wrapping at the end).",
    )
    center: float = Field(
        ge=0.0,
        le=1.0,
        description="Normalized 0..1 position of the opening center along the chosen edge.",
    )
    width: float = Field(
        gt=0.0,
        description="Opening width in meters measured along the chosen boundary edge.",
    )


class Space(StrictModel):
    """
    The room envelope.
    """
    boundary: list[Point2D] = Field(
        min_length=4,
        description="Room boundary polygon vertices in order. The first point should be (0,0).",
    )
    height: float = Field(
        default=2.7,
        gt=0,
        description="Ceiling height in meters.",
    )
    openings: list[Opening] = Field(
        default_factory=list,
        min_length=1,
        description="Doors/windows/openings anchored to boundary edges.",
    )

    @field_validator("boundary")
    @classmethod
    def boundary_must_start_at_origin(cls, boundary: list[Point2D]) -> list[Point2D]:
        first = boundary[0]
        if first.x != 0.0 or first.y != 0.0:
            raise ValueError("Space.boundary[0] must be exactly (0,0).")
        return boundary
