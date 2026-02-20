from __future__ import annotations

from pathlib import Path

from pydantic_ai import Agent, RunContext, ModelRetry
from pydantic_ai.models import Model

from layout_lens.agents.deps import Deps
from layout_lens.schemas.room_plan import RoomPlan
from layout_lens.utilities.utilities import Utilities


class RoomPlanRepairAgent:
    def __init__(self, model) -> None:
        self.agent: Agent[Deps, RoomPlan] = self.build_agent(model)

    def build_agent(self, model: Model) -> Agent[Deps, RoomPlan]:
        agent: Agent[Deps, RoomPlan] = Agent(
            model=model,
            deps_type=Deps,
            output_type=RoomPlan,
            retries=3,
            name='RoomPlanRepairAgent',
        )

        @agent.system_prompt
        def build_system_prompt(ctx: RunContext[Deps]) -> str:
            return (
                "You are a RoomPlan repair assistant.\n"
                "You will be given a failing RoomPlan and a validation error list.\n"
                "Delete the minimum number of elements to solve the validation error list.\n"
                "Rules:\n"
                "- Keep Space unchanged.\n"
                "- Delete the minimum number of elements needed.\n"
                "- Prefer deleting small/duplicate/decorative items first.\n"
                "- Do NOT add new elements.\n"
                "- Output ONLY a valid RoomPlan JSON.\n"
            )
        
        return agent

    def run_sync(
        self,
        user_prompt: str,
        design,
        space,
        failing_plan: RoomPlan,
        validation_message: str,
        deps: Deps,
    ) -> RoomPlan:
        prompt = (
            f"{user_prompt}\n\n"
            "Design intent (JSON):\n"
            f"{design.model_dump_json(indent=2)}\n\n"
            "Space (JSON):\n"
            f"{space.model_dump_json(indent=2)}\n\n"
            "Failing RoomPlan (JSON):\n"
            f"{failing_plan.model_dump_json(indent=2)}\n\n"
            "Validation errors:\n"
            f"{validation_message}\n\n"
            "Repair the plan now."
        )

        repaired_room_plan = self.agent.run_sync(prompt, deps=deps).output

        # best effort to validate - if it still fails, dump and return repaired anyway
        try:
            return deps.geometry_service.validate_room_plan_or_retry(repaired_room_plan, deps.settings)
        except ModelRetry as retry:
            Utilities.write_json(deps.settings.room_plan_output_path, repaired_room_plan)
            Utilities.write_text(deps.settings.validation_error_path, str(retry))
            return repaired_room_plan
