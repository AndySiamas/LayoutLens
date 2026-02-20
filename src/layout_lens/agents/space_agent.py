from __future__ import annotations

from pydantic_ai import Agent, RunContext

from layout_lens.agents.deps import Deps
from layout_lens.schemas.design import Design
from layout_lens.schemas.space import Space


class SpaceAgent:
    def __init__(self, model) -> None:
        self.agent: Agent[Deps, Space] = self._init_agent(model)

    def _init_agent(self, model) -> Agent[Deps, Space]:
        agent: Agent[Deps, Space] = Agent(
            model=model,
            deps_type=Deps,
            output_type=Space,
            retries=5
        )

        @agent.system_prompt
        def build_system_prompt(ctx: RunContext[Deps]) -> str:
            return (f"""
                    /think
                    You are a room envelope planner.
                    Output a Space object that matches the schema EXACTLY. No extra keys.

                    Core rules:
                    - Use meters only. Do not use feet/inches.
                    - The first boundary point must be (0,0).
                    - List boundary points around the perimeter (clockwise OR counterclockwise), consistent ordering.
                    - Choose reasonable overall dimensions based on the user's intent and the provided design intent.
                    - Make rooms slightly bigger than the user requests.

                    Boundary rules:
                    - Use a simple polygon (no self-intersections).
                    - Use 4-10 points unless a more complex shape is clearly required.
                    - Avoid tiny edges; prefer clean, readable shapes.

                    Openings rules (Space.openings):
                    - Openings are doors/windows/other openings anchored to boundary edges.
                    - For most interior spaces, include at least 1 door opening.
                    - If the user requests multiple exits, include 2 door openings on different edges.
                    - If windows are appropriate, include 1-4 window openings.
                    - Pick edge_index values that exist (0..len(boundary)-1). Edge i is boundary[i] -> boundary[i+1], wrapping at the end.
                    - center is normalized 0..1 along the chosen edge; keep it away from corners (avoid values very close to 0 or 1).
                    - width is in meters along the edge; choose realistic sizes:
                    - door: ~0.75-1.2m
                    - window: ~0.6-2.0m
                    - Do not place an opening so wide that it would spill past the edge endpoints.
                    """).strip()
        
        @agent.output_validator
        def validate_space(ctx: RunContext[Deps], space: Space) -> Space:
            return ctx.deps.geometry_service.validate_space_or_retry(space, ctx.deps.settings)

        return agent

    def run_sync(self, user_prompt: str, design: Design, deps: Deps) -> Space:
        combined_prompt = (
            f"{user_prompt}\n\n"
            "Here is the design intent (JSON):\n"
            f"{design.model_dump_json(indent=2)}\n\n"
            "Now produce the Space."
        )
        return self.agent.run_sync(combined_prompt, deps=deps).output
