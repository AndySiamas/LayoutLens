from __future__ import annotations
from dataclasses import dataclass
from pydantic_ai import ModelRetry
import shapely

from .shapely_adapter import ShapelyGeometryAdapter
from layout_lens.schemas.space import Space
from layout_lens.schemas.room_plan import RoomPlan


@dataclass(frozen=True)
class GeometryRules:
    geometry: ShapelyGeometryAdapter

    def validate_space_or_retry(self, space: Space) -> Space:
        room_polygon = self.geometry.create_room_boundary_polygon(space)

        if not room_polygon.is_valid:
            # Optional: shapely.is_valid_reason(room_polygon) if you want details
            print(space)
            raise ModelRetry("Room boundary polygon is invalid (self-intersecting or malformed). Output a simple non-self-intersecting polygon.")

        if room_polygon.area <= 0:
            print(space)
            raise ModelRetry("Room boundary has zero/negative area. Output a valid polygon with positive area.")

        return space

    def validate_room_plan_or_retry(self, plan: RoomPlan) -> RoomPlan:
        room_polygon = self.geometry.create_room_boundary_polygon(plan.space)
        shapely.prepare(room_polygon)  # speeds up repeated predicates :contentReference[oaicite:2]{index=2}

        # inside-room check
        for element in plan.elements:
            if not self.geometry.element_is_inside_room(plan.space, element):
                raise ModelRetry(f"Element '{element.id}' footprint is outside the room boundary. Move it fully inside.")

        # overlap check (NOTE: intersects includes “touching”)
        element_list = list(plan.elements)
        for i in range(len(element_list)):
            for j in range(i + 1, len(element_list)):
                a = self.geometry.create_element_footprint_polygon(element_list[i])
                b = self.geometry.create_element_footprint_polygon(element_list[j])

                # If you want “touching is OK”, reject only if they intersect AND not just touch
                if a.intersects(b) and not a.touches(b):
                    raise ModelRetry(
                        f"Elements '{element_list[i].id}' and '{element_list[j].id}' overlap. Reposition them so they do not overlap."
                    )

        return plan
