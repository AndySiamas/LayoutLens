from layout_lens.schemas.room_plan import (
    RoomPlan, Space, Point2D, Element, Transform2D, RectFootprint
)
from layout_lens.core.geometry.shapely_adapter import ShapelyGeometryAdapter


def main() -> None:
    plan = RoomPlan(
        schema_version="0.1",
        room_grid_size=0.25,
        space=Space(
            boundary=[
                Point2D(x=0, y=0),
                Point2D(x=5, y=0),
                Point2D(x=5, y=4),
                Point2D(x=0, y=4),
            ],
            height=2.7,
        ),
        elements=[
            Element(
                id="bed_1",
                label="Bed",
                type="furniture",
                transform=Transform2D(x=2.0, y=2.0, yaw_deg=0),
                footprint=RectFootprint(kind="rect", width=2.0, depth=1.6),
            ),
            Element(
                id="desk_1",
                label="Desk",
                type="furniture",
                transform=Transform2D(x=2.6, y=2.0, yaw_deg=0),
                footprint=RectFootprint(kind="rect", width=1.2, depth=0.6),
            ),
        ],
    )

    adapter = ShapelyGeometryAdapter()

    # Schema test: can serialize cleanly
    print("Schema OK. JSON length:", len(plan.model_dump_json(indent=2)))

    # Geometry tests
    room_polygon = adapter.create_room_boundary_polygon(plan.space)
    print("Room area:", room_polygon.area)

    for element in plan.elements:
        inside = adapter.element_is_inside_room(plan.space, element)
        print(f"{element.id} inside room:", inside)

    overlaps = adapter.any_elements_overlap(plan.elements)
    print("Any overlaps:", overlaps)


if __name__ == "__main__":
    main()
