from pathlib import Path

from pydantic_ai import exceptions as pai_exc
from pydantic_ai.usage import RunUsage

from layout_lens.agents.deps import Deps
from layout_lens.agents.design_agent import DesignAgent
from layout_lens.agents.space_agent import SpaceAgent
from layout_lens.agents.room_plan_agent import RoomPlanAgent
from layout_lens.core.settings import Settings
from layout_lens.core.geometry.geometry_service import GeometryService
from layout_lens.llm.model_factory import ModelFactory
from layout_lens.schemas.room_plan import RoomPlan
from layout_lens.utilities.utilities import Utilities

class Application:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def run(self, user_prompt: str) -> str:
        run_id: str = Utilities.make_run_id()
        run_output_dir_path: Path = self.settings.output_dir_path / run_id
        self.settings.set_run_output_dir(run_output_dir_path)
        Utilities.reset_dir(self.settings.run_output_dir_path)

        model = ModelFactory.create_model(self.settings)

        deps = Deps(
            settings=self.settings,
            geometry_service=GeometryService()
        )

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

        completion_message = f"Application complete! Output folder: {self.settings.run_output_dir_path.resolve()}"
        return completion_message