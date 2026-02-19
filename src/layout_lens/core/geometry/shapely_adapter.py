from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable
from shapely.affinity import rotate as shapely_rotate
from shapely.affinity import translate as shapely_translate
from shapely.geometry import Polygon, box
from shapely.prepared import prep as shapely_prepare

from layout_lens.schemas.space import Space
from layout_lens.schemas.room_plan import Element, RectFootprint, PolyFootprint


@dataclass(frozen=True)
class ShapelyGeometryAdapter:
    """
    Converts our Pydantic RoomPlan schema objects into Shapely geometry.
    """

    def create_room_boundary_polygon(self, space: Space) -> Polygon:
        """Room boundary polygon in world coordinates (meters)."""
        boundary_coordinates = [(point.x, point.y) for point in space.boundary]
        return Polygon(boundary_coordinates)

    def create_element_footprint_polygon(self, element: Element) -> Polygon:
        """
        Element footprint polygon in world coordinates (meters).

        - Builds the footprint in the element's local space
        - Rotates by element.transform.yaw_deg around local origin (0,0)
        - Translates to element.transform.(x,y)
        """
        local_footprint_polygon = self._create_local_footprint_polygon(element)
        rotated_polygon = shapely_rotate(
            local_footprint_polygon,
            element.transform.yaw_deg,
            origin=(0.0, 0.0),
            use_radians=False,
        )
        world_polygon = shapely_translate(
            rotated_polygon,
            xoff=element.transform.x,
            yoff=element.transform.y,
        )
        return world_polygon

    def create_clearance_polygon(self, element: Element, clearance_meters: float) -> Polygon:
        """
        Returns the 'keep-out' area around an element (footprint buffered by clearance).
        Useful for walkway/door-clearance rules.
        """
        element_polygon = self.create_element_footprint_polygon(element)
        return element_polygon.buffer(clearance_meters)

    def element_is_inside_room(self, space: Space, element: Element) -> bool:
        """
        True if the element footprint is fully inside (or on) the room boundary.
        Uses 'covers' so touching the boundary is allowed.
        """
        room_polygon = self.create_room_boundary_polygon(space)
        element_polygon = self.create_element_footprint_polygon(element)
        return room_polygon.covers(element_polygon)

    def any_elements_overlap(self, elements: Iterable[Element]) -> bool:
        """
        Simple overlap check: returns True if any two element polygons intersect.
        (We can refine later to allow 'touching' if you want.)
        """
        element_list = list(elements)
        element_polygons = [self.create_element_footprint_polygon(e) for e in element_list]

        for i in range(len(element_polygons)):
            for j in range(i + 1, len(element_polygons)):
                if element_polygons[i].intersects(element_polygons[j]):
                    return True
        return False

    def prepare_room_boundary(self, space: Space):
        """
        Prepared geometry speeds up repeated spatial predicates (many contains/intersects checks).
        Return value is a Shapely prepared geometry object.
        """
        return shapely_prepare(self.create_room_boundary_polygon(space))

    # ---- internal helpers ----

    def _create_local_footprint_polygon(self, element: Element) -> Polygon:
        """
        Build the footprint polygon in element-local coordinates.
        Convention:
          - local origin (0,0) is the element center
          - rect footprint extends +/- width/2 and +/- depth/2
        """
        footprint = element.footprint

        if isinstance(footprint, RectFootprint):
            half_width = footprint.width / 2.0
            half_depth = footprint.depth / 2.0
            return box(-half_width, -half_depth, half_width, half_depth)

        if isinstance(footprint, PolyFootprint):
            local_coordinates = [(point.x, point.y) for point in footprint.vertices]
            return Polygon(local_coordinates)

        raise TypeError(f"Unsupported footprint type: {type(footprint)!r}")
