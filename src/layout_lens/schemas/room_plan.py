from __future__ import annotations

from typing import Any, Annotated, Literal, Union
from enum import Enum

from pydantic import Field

from .base import StrictModel
from .space import Point2D, Space

# ---------------------------------------------------------------------
# Helper types
# ---------------------------------------------------------------------

ElementId = Annotated[
    str,
    Field(
        min_length=1,
        max_length=64,
        pattern=r"^[a-z][a-z0-9_]*$",
        description="Stable identifier (e.g., 'bed_01', 'pew_12'). Lowercase + underscores only.",
    ),
]

ShortText = Annotated[
    str,
    Field(
        min_length=1,
        max_length=100,
        description="Short human-readable text.",
    ),
]


# ---------------------------------------------------------------------
# Shared primitives
# ---------------------------------------------------------------------

class Transform2D(StrictModel):
    """
    2D placement in the same coordinate system as Space (meters + degrees).

    Notes for the model:
    - (x, y) is the element's *center point* in meters.
    - yaw_deg rotates the footprint around its center.
    """
    x: float = Field(description="Center X in meters.")
    y: float = Field(description="Center Y in meters.")
    yaw_deg: int = Field(
        default=0,
        ge=-180,
        le=180,
        multiple_of=90,
        description="Rotation in degrees around the element center. Use only -180, -90, 0, 90, 180.",
    )


# ---------------------------------------------------------------------
# Element footprints (2D shapes)
# ---------------------------------------------------------------------

class RectFootprint(StrictModel):
    """A rectangular footprint in meters (before rotation)."""
    kind: Literal["rect"] = "rect"
    width: float = Field(gt=0, description="Width in meters (local X axis).")
    depth: float = Field(gt=0, description="Depth in meters (local Y axis).")


class PolyFootprint(StrictModel):
    """
    Polygon footprint vertices in meters, in the element's *local* space
    (before applying Transform2D).
    """
    kind: Literal["poly"] = "poly"
    vertices: list[Point2D] = Field(
        min_length=3,
        description="Polygon vertices in local coordinates (meters).",
    )


Footprint = Annotated[
    Union[RectFootprint, PolyFootprint],
    Field(discriminator="kind"),
]


# ---------------------------------------------------------------------
# Placement (collision intent)
# ---------------------------------------------------------------------
class Placement(str, Enum):
    """
    How the element is installed (affects validation):

    - floor: occupies floor space (must be inside boundary and should not overlap other floor items)
    - on: sits on another object (may overlap in 2D; usually excluded from floor collision checks)
    - wall: mounted on a wall (usually excluded from floor collision checks)
    """
    FLOOR = "floor"
    ON = "on"
    WALL = "wall"


# ---------------------------------------------------------------------
# Elements
# ---------------------------------------------------------------------
class Element(StrictModel):
    """
    A placed item.

    Important:
    - footprint + transform describe its 2D region (meters).
    - placement tells the validator whether to treat it as a floor-collider.
    """
    id: ElementId = Field(description="Unique id for this element.")
    label: ShortText = Field(description="Plain-English item name/type (e.g., 'desk', 'altar', 'kettle').")

    placement: Placement = Field(
        default=Placement.FLOOR,
        description=(
            "Installation type: "
            "'floor' occupies floor space and must NOT overlap other floor items; "
            "'on' means it sits on top of another element (can overlap in 2D); "
            "'wall' means it is wall-mounted (must be near boundary) (can overlap in 2D)."
        ),
    )

    transform: Transform2D = Field(description="Center position + rotation (meters + degrees).")
    footprint: Footprint = Field(description="2D footprint shape in meters (used for bounds/collision).")


# ---------------------------------------------------------------------
# Top-level plan
# ---------------------------------------------------------------------
class RoomPlan(StrictModel):
    """
    A complete plan for ONE room.

    - space: the room envelope polygon (container)
    - elements: placed items (some collide on the floor, others may be on/wall-mounted)
    """
    space: Space = Field(description="Room envelope (boundary polygon + height).")
    elements: list[Element] = Field(default_factory=list, description="Placed items in the room.")
    room_grid_size: float = Field(
        gt=0,
        default=0.25,
        description="Grid resolution in meters for snapping/ASCII rendering.",
    )
