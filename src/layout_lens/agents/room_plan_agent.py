from __future__ import annotations
from pathlib import Path

from pydantic_ai import Agent, RunContext, ModelRetry
from pydantic_ai import exceptions as pai_exc
from pydantic_ai.models import Model

from layout_lens.utilities.utilities import Utilities
from layout_lens.agents.deps import Deps
from layout_lens.agents.room_plan_repair_agent import RoomPlanRepairAgent
from layout_lens.schemas.design import Design
from layout_lens.schemas.space import Space
from layout_lens.schemas.room_plan import RoomPlan


class RoomPlanAgent:
    def __init__(self, model: Model) -> None:
        self.agent: Agent[Deps, RoomPlan] = self.build_agent(model)
        self.repair_agent = RoomPlanRepairAgent(model)

    def build_agent(self, model: Model) -> Agent[Deps, RoomPlan]:
        agent: Agent[Deps, RoomPlan] = Agent(
            model=model,
            deps_type=Deps,
            output_type=RoomPlan,
            retries=7,
            name="RoomPlanAgent",
        )

        @agent.system_prompt
        def system_prompt(ctx: RunContext[Deps]) -> str:
            return (f"""
                    /think\n
                    You are a room layout planner.\n
                    Return ONLY a RoomPlan JSON that matches the schema EXACTLY. No extra keys.\n\n
                    Rules:\n
                    - Use METERS only.\n
                    - RoomPlan.space MUST match the provided SPACE exactly (boundary + height).\n
                    - Every element must be fully inside the room boundary.\n
                    - Do NOT cram the room with elements. 
                    - Generally prefer to only use a few bigger elements than a lot of small elements.\n
                    - Only FLOOR elements must avoid overlapping other FLOOR elements.\n
                    - Use placement correctly:\n
                      * floor = occupies floor space (furniture, counters, seating, large fixtures)\n
                      * on    = sits on another element (mugs, kettles, small items on counters/shelves)\n
                      * wall  = mounted on wall (menus, sconces, framed art)\n
                    - Only FLOOR elements must not overlap other FLOOR elements.
                    - Do NOT create non-tangible zones, areas, or rooms as elements (e.g., 'entrance', 'closet', 'aisle', 'walkway'). Only real items.
                    - Do NOT add extra rooms.
                    - Small decor should be 'on' or 'wall' (not 'floor') unless it truly occupies floor space.
                    - Chairs must not overlap tables. Keep at least 0.10m gap between chair and table footprints.
                    - Prefer realistic footprints; keep yaw_deg to 0/90/180/270.\n
                    - room_grid_size defaults to {ctx.deps.settings.room_grid_size}.\n
                    """)

        @agent.output_validator
        def validate_room_plan(ctx: RunContext[Deps], plan: RoomPlan) -> RoomPlan:
            # Always dump the last parsed candidate, even if geometry validation fails.
            Utilities.write_json(ctx.deps.settings.room_plan_output_path, plan)

            try:
                return ctx.deps.geometry_service.validate_room_plan_or_retry(plan)
            except ModelRetry as retry:
                Utilities.write_text(ctx.deps.settings.validation_error_path, str(retry))
                raise

        return agent

    def run_sync(self, user_prompt: str, design: Design, space: Space, deps: Deps) -> RoomPlan:
        prompt = (
            "USER REQUEST:\n"
            f"{user_prompt}\n\n"
            "DESIGN JSON:\n"
            f"{design.model_dump_json(indent=2)}\n\n"
            "SPACE JSON:\n"
            f"{space.model_dump_json(indent=2)}\n\n"
            "TASK:\n"
            "Produce a RoomPlan JSON. Keep RoomPlan.space identical to SPACE.\n"
        ).strip()

        try:
            return self.agent.run_sync(prompt, deps=deps).output
        
        except pai_exc.UnexpectedModelBehavior as exc:
            failing_room_plan_path: Path = deps.settings.room_plan_output_path
            if not failing_room_plan_path.exists():
                # No parsed candidate exists to repair; re-raise the real failure.
                raise

            failing_room_plan = RoomPlan.model_validate_json(failing_room_plan_path.read_text(encoding='utf-8'))

            # Prefer the last stored validation error (most reliable).
            validation_error_message = ""
            if deps.settings.validation_error_path.exists():
                validation_error_message = deps.settings.validation_error_path.read_text(encoding="utf-8").strip()

            # Fallback: still pass something meaningful if the file is missing.
            if not validation_error_message:
                validation_error_message = str(exc)

            repaired_room_plan = self.repair_agent.run_sync(
                user_prompt=user_prompt,
                design=design,
                space=space,
                failing_plan=failing_room_plan,
                validation_message=validation_error_message,
                deps=deps,
            )
            return repaired_room_plan
