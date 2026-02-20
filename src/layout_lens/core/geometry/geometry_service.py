from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from shapely.affinity import rotate as shapely_rotate, translate as shapely_translate
from shapely.geometry import MultiPolygon, Point, Polygon, box
from shapely.geometry.base import BaseGeometry
from shapely.ops import nearest_points

from pydantic_ai import ModelRetry

from layout_lens.core.settings import Settings
from layout_lens.utilities.utilities import Utilities
from layout_lens.schemas.room_plan import (
    Element,
    Placement,
    PolyFootprint,
    RectFootprint,
    RoomPlan,
    Space,
)


@dataclass(frozen=True)
class GeometryService:
    boundary_tolerance: float = 0.02  # expand room slightly for "barely outside"
    boundary_margin: float = 0.05  # extra breathing room when suggesting fixes
    overlap_area_tolerance: float = 0.002  # ignore tiny intersections
    overlap_separation_margin: float = 0.10  # how much to separate beyond overlap
    max_reported_overlap_pairs: int = 12
    wall_max_distance: float = 0.35  # "near wall" requirement for WALL placement
    validation_error_path: Path = Path("./runs/validation_error.txt")

    # -------------------------
    # Geometry construction
    # -------------------------
    def create_room_polygon(self, space: Space) -> Polygon:
        return Polygon([(point.x, point.y) for point in space.boundary])

    def create_element_polygon(self, element: Element) -> Polygon:
        local_footprint_polygon = self._create_local_footprint_polygon(element)
        rotated_polygon = shapely_rotate(
            local_footprint_polygon,
            element.transform.yaw_deg,
            origin=(0.0, 0.0),
            use_radians=False,
        )
        return shapely_translate(
            rotated_polygon,
            xoff=element.transform.x,
            yoff=element.transform.y,
        )

    def _create_local_footprint_polygon(self, element: Element) -> Polygon:
        footprint = element.footprint
        if isinstance(footprint, RectFootprint):
            half_width_m = footprint.width / 2.0
            half_depth_m = footprint.depth / 2.0
            return box(-half_width_m, -half_depth_m, half_width_m, half_depth_m)

        if isinstance(footprint, PolyFootprint):
            return Polygon([(p.x, p.y) for p in footprint.vertices])

        raise TypeError(f"Unsupported footprint type: {type(footprint)!r}")

    # -------------------------
    # Validation entrypoints
    # -------------------------
    def validate_space_or_retry(self, space: Space, settings: Settings) -> Space:
        room_polygon = self.create_room_polygon(space)

        if not room_polygon.is_valid:
            raise ModelRetry("Space boundary polygon is invalid. Output a simple non-self-intersecting polygon.")
        if room_polygon.area <= 0:
            raise ModelRetry("Space boundary polygon has zero/negative area. Output a polygon with positive area.")

        if not space.openings:
            return space

        boundary_points = space.boundary
        boundary_point_count = len(boundary_points)
        corner_clearance = self.boundary_margin

        issues: list[str] = []

        for opening_number, opening in enumerate(space.openings, start=1):
            edge_index = opening.edge_index
            if edge_index >= boundary_point_count:
                issues.append(
                    f"Opening #{opening_number} ({opening.kind}) edge_index={edge_index} is out of range "
                    f"(0..{boundary_point_count - 1})."
                )
                continue

            edge_start = boundary_points[edge_index]
            edge_end = boundary_points[(edge_index + 1) % boundary_point_count]

            edge_delta_x = edge_end.x - edge_start.x
            edge_delta_y = edge_end.y - edge_start.y
            edge_length = math.hypot(edge_delta_x, edge_delta_y)

            if edge_length == 0.0:
                issues.append(
                    f"Opening #{opening_number} ({opening.kind}) is on a zero-length edge (edge_index={edge_index}). "
                    "Fix the boundary points or choose a different edge."
                )
                continue

            required_edge_length = opening.width + (2.0 * corner_clearance)
            if required_edge_length > edge_length:
                issues.append(
                    f"Opening #{opening_number} ({opening.kind}) width={opening.width:.2f} is too large for "
                    f"edge_index={edge_index} (edge length ≈ {edge_length:.2f}). "
                    "Reduce width or choose a longer edge."
                )
                continue

            half_opening_width = opening.width / 2.0
            minimum_center_distance_from_edge_start = half_opening_width + corner_clearance

            minimum_center = minimum_center_distance_from_edge_start / edge_length
            maximum_center = 1.0 - minimum_center

            if opening.center < minimum_center or opening.center > maximum_center:
                issues.append(
                    f"Opening #{opening_number} ({opening.kind}) center={opening.center:.2f} is too close to a corner "
                    f"for width={opening.width:.2f} on edge_index={edge_index}. "
                    f"Use center in approximately [{minimum_center:.2f}, {maximum_center:.2f}]."
                )

        if issues:
            error_message: str = (
                "RoomPlan validation failed. Fix ALL issues below and retry.\n"
                + "\n".join(f"{i + 1}) {msg}" for i, msg in enumerate(issues))
            )
            Utilities.write_text(settings.validation_error_path, error_message)
            raise ModelRetry(error_message)

        return space


    def validate_room_plan_or_retry(self, plan: RoomPlan, settings: Settings) -> RoomPlan:
        room_polygon = self.create_room_polygon(plan.space)
        tolerant_room_polygon = room_polygon.buffer(self.boundary_tolerance)

        issues: list[str] = []
        issues += self._collect_duplicate_id_issues(plan.elements)

        element_polygons_by_id: dict[str, Polygon] = {
            element.id: self.create_element_polygon(element) for element in plan.elements
        }

        issues += self._collect_bounds_issues(tolerant_room_polygon, plan.elements, element_polygons_by_id)
        issues += self._collect_floor_overlap_issues(tolerant_room_polygon, plan.elements, element_polygons_by_id)
        issues += self._collect_near_duplicate_floor_items(plan.elements)

        if issues:
            error_message: str = (
                "RoomPlan validation failed. Fix ALL issues below and retry.\n"
                "Reminder: keep RoomPlan.space unchanged\n"
                + "\n".join(f"{i + 1}) {msg}" for i, msg in enumerate(issues))
            )
            Utilities.write_text(settings.validation_error_path, error_message)
            raise ModelRetry(error_message)

        return plan

    # -------------------------
    # Issues
    # -------------------------
    def _collect_duplicate_id_issues(self, elements: Iterable[Element]) -> list[str]:
        seen_ids: set[str] = set()
        duplicate_ids: set[str] = set()

        for element in elements:
            if element.id in seen_ids:
                duplicate_ids.add(element.id)
            seen_ids.add(element.id)

        if not duplicate_ids:
            return []

        return [f"Duplicate element ids found: {', '.join(sorted(duplicate_ids))}. Make every element.id unique."]

    def _collect_bounds_issues(
        self,
        tolerant_room_polygon: Polygon,
        elements: Iterable[Element],
        element_polygons_by_id: dict[str, Polygon],
    ) -> list[str]:
        issues: list[str] = []

        for element in elements:
            element_polygon = element_polygons_by_id[element.id]
            element_center_point = Point(element.transform.x, element.transform.y)

            # WALL: center inside + near boundary
            if element.placement == Placement.WALL:
                if not tolerant_room_polygon.covers(element_center_point):
                    issues.append(
                        f"Wall element '{element.id}' ({element.label}) center is outside room. "
                        "Move its center just inside the boundary."
                    )
                    continue

                distance_to_wall_m = tolerant_room_polygon.boundary.distance(element_center_point)
                if distance_to_wall_m > self.wall_max_distance:
                    issues.append(
                        f"Wall element '{element.id}' ({element.label}) should be near a wall. "
                        f"Move its center within ~{self.wall_max_distance:.2f}m of the boundary."
                    )
                continue

            # ON: center inside only
            if element.placement == Placement.ON:
                if not tolerant_room_polygon.covers(element_center_point):
                    issues.append(
                        f"On-element '{element.id}' ({element.label}) center is outside room. "
                        "Move its center inside the boundary."
                    )
                continue

            # FLOOR: require full footprint inside
            if tolerant_room_polygon.covers(element_polygon):
                continue

            suggested_translation = self._suggest_translation_into_room(
                room_polygon=tolerant_room_polygon,
                element_polygon=element_polygon,
                inset_margin_m=self.boundary_margin,
                max_iterations=6,
            )

            if suggested_translation is None:
                issues.append(
                    f"Element '{element.id}' ({element.label}) is outside the room and cannot fit with its current "
                    "size/rotation. Shrink its footprint and/or rotate it so it fits fully inside."
                )
                continue

            delta_x_m, delta_y_m = suggested_translation
            new_center_x_m = element.transform.x + delta_x_m
            new_center_y_m = element.transform.y + delta_y_m

            if abs(delta_x_m) < 1e-3 and abs(delta_y_m) < 1e-3:
                issues.append(
                    f"Element '{element.id}' ({element.label}) is outside the room boundary (likely near a slanted wall). "
                    "Move it inward so the entire footprint is inside the polygon."
                )
            else:
                issues.append(
                    f"Element '{element.id}' ({element.label}) is outside the room boundary. "
                    f"Move its center by approximately Δx={delta_x_m:.2f}m, Δy={delta_y_m:.2f}m "
                    f"to new center=({new_center_x_m:.2f}, {new_center_y_m:.2f})."
                )

        return issues

    def _collect_floor_overlap_issues(
        self,
        room_for_clamp_polygon: Polygon,
        elements: list[Element],
        element_polygons_by_id: dict[str, Polygon],
    ) -> list[str]:
        floor_elements = [element for element in elements if element.placement == Placement.FLOOR]
        if len(floor_elements) < 2:
            return []

        issues: list[str] = []
        reported_overlap_pairs = 0

        for i in range(len(floor_elements)):
            element_a = floor_elements[i]
            element_a_polygon = element_polygons_by_id[element_a.id]

            for j in range(i + 1, len(floor_elements)):
                element_b = floor_elements[j]
                element_b_polygon = element_polygons_by_id[element_b.id]

                # overlap = intersects AND NOT touches (touching edges ok)
                if not element_a_polygon.intersects(element_b_polygon) or element_a_polygon.touches(element_b_polygon):
                    continue

                overlap_area_m2 = element_a_polygon.intersection(element_b_polygon).area
                if overlap_area_m2 <= self.overlap_area_tolerance:
                    continue

                reported_overlap_pairs += 1
                if reported_overlap_pairs > self.max_reported_overlap_pairs:
                    return [
                        f"More than {self.max_reported_overlap_pairs} overlapping floor-element pairs detected. "
                        "Spread floor elements out / reduce sizes and retry."
                    ]

                issues.append(
                    self._format_floor_overlap_fix(
                        room_for_clamp_polygon,
                        element_a,
                        element_a_polygon,
                        element_b,
                        element_b_polygon,
                    )
                )

        return issues

    def _collect_near_duplicate_floor_items(self, elements: list[Element]) -> list[str]:
        floor_elements = [element for element in elements if element.placement == Placement.FLOOR]
        issues: list[str] = []

        for i in range(len(floor_elements)):
            for j in range(i + 1, len(floor_elements)):
                element_a, element_b = floor_elements[i], floor_elements[j]
                if element_a.label != element_b.label:
                    continue
                if abs(element_a.transform.x - element_b.transform.x) < 0.05 and abs(
                    element_a.transform.y - element_b.transform.y
                ) < 0.05:
                    issues.append(
                        f"Floor elements '{element_a.id}' and '{element_b.id}' look like duplicates "
                        "(same label and nearly same position). Delete one of them or move it clearly elsewhere."
                    )

        return issues

    # -------------------------
    # Suggestions / messaging
    # -------------------------
    def _suggest_translation_into_room(
        self,
        *,
        room_polygon: Polygon,
        element_polygon: Polygon,
        inset_margin_m: float,
        max_iterations: int = 6,
        overshoot_multiplier: float = 1.05,
    ) -> tuple[float, float] | None:
        """
        Suggest a translation (delta_x_m, delta_y_m) that moves the *entire* element_polygon inside room_polygon.

        Uses an inset "safe" polygon (negative buffer) to avoid placements that are barely inside.

        Robust for partially-overlapping geometries by computing a push vector from the polygonal
        outside fragment (avoids nearest_points(...) returning a 0-length move).
        """
        safe_room_polygon = room_polygon.buffer(-inset_margin_m)
        if safe_room_polygon.is_empty:
            safe_room_polygon = room_polygon

        if safe_room_polygon.covers(element_polygon):
            return (0.0, 0.0)

        accumulated_delta_x_m = 0.0
        accumulated_delta_y_m = 0.0
        translated_element_polygon = element_polygon

        for _ in range(max_iterations):
            if safe_room_polygon.covers(translated_element_polygon):
                return (accumulated_delta_x_m, accumulated_delta_y_m)

            outside_fragment = translated_element_polygon.difference(safe_room_polygon)
            if outside_fragment.is_empty:
                break

            push_vector = self._compute_inward_push_vector_from_outside_fragment(
                outside_fragment=outside_fragment,
                safe_room_polygon=safe_room_polygon,
            )
            if push_vector is None:
                break

            step_delta_x_m, step_delta_y_m = push_vector
            step_delta_x_m *= overshoot_multiplier
            step_delta_y_m *= overshoot_multiplier

            accumulated_delta_x_m += step_delta_x_m
            accumulated_delta_y_m += step_delta_y_m
            translated_element_polygon = shapely_translate(
                translated_element_polygon, xoff=step_delta_x_m, yoff=step_delta_y_m
            )

        if room_polygon.covers(translated_element_polygon):
            return (accumulated_delta_x_m, accumulated_delta_y_m)

        return None

    def _suggest_center_to_fit_room_bounds(
        self,
        *,
        room_bounds: tuple[float, float, float, float],
        element_poly: Polygon,
        current_center: tuple[float, float],
        margin: float,
    ) -> tuple[float, float] | None:
        room_min_x, room_min_y, room_max_x, room_max_y = room_bounds
        element_min_x, element_min_y, element_max_x, element_max_y = element_poly.bounds
        center_x, center_y = current_center

        left_extent = center_x - element_min_x
        right_extent = element_max_x - center_x
        bottom_extent = center_y - element_min_y
        top_extent = element_max_y - center_y

        min_center_x = room_min_x + left_extent + margin
        max_center_x = room_max_x - right_extent - margin
        min_center_y = room_min_y + bottom_extent + margin
        max_center_y = room_max_y - top_extent - margin

        if min_center_x > max_center_x or min_center_y > max_center_y:
            return None

        return (
            self._clamp(center_x, min_center_x, max_center_x),
            self._clamp(center_y, min_center_y, max_center_y),
        )

    def _format_floor_overlap_fix(
        self,
        room_for_clamp_polygon: Polygon,
        element_a: Element,
        element_a_polygon: Polygon,
        element_b: Element,
        element_b_polygon: Polygon,
    ) -> str:
        a_min_x, a_min_y, a_max_x, a_max_y = element_a_polygon.bounds
        b_min_x, b_min_y, b_max_x, b_max_y = element_b_polygon.bounds

        # How far B must move (plus margin) to be fully separated from A along each axis direction.
        separation_margin = self.overlap_separation_margin
        push_right = (a_max_x - b_min_x) + separation_margin
        push_left = (b_max_x - a_min_x) + separation_margin
        push_up = (a_max_y - b_min_y) + separation_margin
        push_down = (b_max_y - a_min_y) + separation_margin

        candidate_moves: list[tuple[float, float]] = [
            (push_right, 0.0),
            (-push_left, 0.0),
            (0.0, push_up),
            (0.0, -push_down),
        ]

        # Prefer smaller moves first.
        candidate_moves.sort(key=lambda d: abs(d[0]) + abs(d[1]))

        chosen_move: tuple[float, float] | None = None

        for candidate_dx, candidate_dy in candidate_moves:
            total_dx, total_dy = candidate_dx, candidate_dy
            moved_polygon = shapely_translate(element_b_polygon, xoff=total_dx, yoff=total_dy)

            # If we pushed outside the room, clamp it back in (but keep the overall move).
            if not room_for_clamp_polygon.covers(moved_polygon):
                correction = self._suggest_translation_into_room(
                    room_polygon=room_for_clamp_polygon,
                    element_polygon=moved_polygon,
                    inset_margin_m=self.boundary_margin,
                    max_iterations=6,
                )
                if correction is None:
                    continue
                correction_dx, correction_dy = correction
                total_dx += correction_dx
                total_dy += correction_dy
                moved_polygon = shapely_translate(element_b_polygon, xoff=total_dx, yoff=total_dy)

            # Must be inside AND must actually eliminate the overlap (touching edges is OK).
            if not room_for_clamp_polygon.covers(moved_polygon):
                continue
            if moved_polygon.intersects(element_a_polygon) and not moved_polygon.touches(element_a_polygon):
                continue

            chosen_move = (total_dx, total_dy)
            break

        if chosen_move is None:
            return (
                f"Floor elements overlap: '{element_a.id}' ({element_a.label}) and '{element_b.id}' ({element_b.label}). "
                f"Unable to find a simple nudge for '{element_b.id}' that stays inside the room and removes the overlap. "
                "Resize/rotate/move one of them, or delete a smaller/less important item."
            )

        move_x, move_y = chosen_move
        b_center_x, b_center_y = element_b.transform.x, element_b.transform.y
        new_b_center_x = b_center_x + move_x
        new_b_center_y = b_center_y + move_y

        return (
            f"Floor elements overlap: '{element_a.id}' ({element_a.label}) and '{element_b.id}' ({element_b.label}). "
            f"Move ONLY '{element_b.id}' by about Δx={move_x:.2f}m, Δy={move_y:.2f}m "
            f"to new center=({new_b_center_x:.2f}, {new_b_center_y:.2f}), or resize/rotate it to eliminate the overlap."
        )

    # -------------------------
    # Debug / utils
    # -------------------------
    @staticmethod
    def _clamp(value: float, low: float, high: float) -> float:
        return max(low, min(value, high))

    def _compute_inward_push_vector_from_outside_fragment(
        self,
        *,
        outside_fragment: BaseGeometry,
        safe_room_polygon: Polygon,
    ) -> tuple[float, float] | None:
        outside_polygons = self._extract_polygon_components(outside_fragment)
        if not outside_polygons:
            return None

        best_delta_x_m = 0.0
        best_delta_y_m = 0.0
        best_distance_m = -1.0

        for outside_polygon in outside_polygons:
            for vertex_x, vertex_y in outside_polygon.exterior.coords:
                vertex_point = Point(vertex_x, vertex_y)

                if safe_room_polygon.covers(vertex_point):
                    continue

                nearest_point_on_safe_room = nearest_points(vertex_point, safe_room_polygon)[1]
                candidate_delta_x_m = nearest_point_on_safe_room.x - vertex_x
                candidate_delta_y_m = nearest_point_on_safe_room.y - vertex_y
                candidate_distance_m = math.hypot(candidate_delta_x_m, candidate_delta_y_m)

                if candidate_distance_m > best_distance_m:
                    best_distance_m = candidate_distance_m
                    best_delta_x_m = candidate_delta_x_m
                    best_delta_y_m = candidate_delta_y_m

        if best_distance_m <= 1e-9:
            return None

        return (best_delta_x_m, best_delta_y_m)

    @staticmethod
    def _extract_polygon_components(geometry: BaseGeometry) -> list[Polygon]:
        if isinstance(geometry, Polygon):
            return [geometry]
        if isinstance(geometry, MultiPolygon):
            return list(geometry.geoms)

        polygons: list[Polygon] = []
        sub_geometries = getattr(geometry, "geoms", None)
        if sub_geometries is None:
            return polygons

        for sub_geometry in sub_geometries:
            if isinstance(sub_geometry, Polygon):
                polygons.append(sub_geometry)
            elif isinstance(sub_geometry, MultiPolygon):
                polygons.extend(list(sub_geometry.geoms))

        return polygons
