from pathlib import Path

from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai import exceptions as pai_exc

from layout_lens.agents.deps import Deps
from layout_lens.agents.design_agent import DesignAgent
from layout_lens.agents.space_agent import SpaceAgent
from layout_lens.agents.room_plan_agent import RoomPlanAgent
from layout_lens.core.settings import Settings
from layout_lens.core.geometry.geometry_service import GeometryService
from layout_lens.schemas.room_plan import RoomPlan
from layout_lens.utilities.utilities import Utilities


class Application:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def run(self) -> None:
        Utilities.reset_dir(self.settings.runs_dir_path)

        provider = OpenAIProvider(base_url=self.settings.llm_base_url)
        model = OpenAIChatModel(model_name=self.settings.llm_model, provider=provider)

        deps = Deps(
            settings=self.settings,
            geometry_service=GeometryService()
        )

        user_prompt = (f"""
                       Take your time and think carefully. Design the interior layout for a small neighborhood coffee shop. It should feel cozy and functional. - An ordering counter with a point-of-sale area - An espresso machine behind the counter - A pickup area that doesn’t block the entrance - A small pastry display - At least 1 customer table with chairs - A menu board on a wall - Some kind of storage (cabinets or shelving) for supplies - At least one trash bin
                        """) 

        try:
            design_agent = DesignAgent(model)
            design = design_agent.run_sync(user_prompt, deps)
            Utilities.write_json(self.settings.design_output_path, design)

            space_agent = SpaceAgent(model)
            space = space_agent.run_sync(user_prompt, design, deps)
            Utilities.write_json(self.settings.space_output_path, space)

            room_plan_agent = RoomPlanAgent(model)
            room_plan = room_plan_agent.run_sync(
                user_prompt=user_prompt,
                design=design,
                space=space,
                deps=deps,
            )
            Utilities.write_json(self.settings.room_plan_output_path, room_plan)
            print('Application complete!')

        except pai_exc.UnexpectedModelBehavior as e:
            retry_msg = Utilities.unwrap_model_retry_message(e)
            if retry_msg:
                print("\n=== RoomPlan validation message ===\n")
                print(retry_msg)
            else:
                raise
