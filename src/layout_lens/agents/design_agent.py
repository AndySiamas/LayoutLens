from __future__ import annotations

from pydantic_ai import Agent, RunContext, NativeOutput
from pydantic_ai.models import Model

from layout_lens.agents.deps import Deps
from layout_lens.schemas.design import Design


class DesignAgent:
    def __init__(self, model) -> None:
        self.agent: Agent[Deps, Design] = self._init_agent(model)

    def _init_agent(self, model) -> Agent[Deps, Design]:
        agent: Agent[Deps, Design] = Agent(
            model=model,
            deps_type=Deps,
            output_type=Design,
            retries=3
        )

        @agent.system_prompt
        def create_system_prompt(ctx: RunContext[Deps]) -> str:
            return (f"""
                    /think\n
                    You are an interior design intent extractor.
                    Output a Design object that matches the schema EXACTLY.
                    Rules:
                        - Take your time. Think long and hard to get the best output possible.
                        - Use meters only. Do NOT use feet or inches.
                        - Do NOT ask questions.
                        - Do NOT add extra JSON keys.
                    """)
        
        return agent

    def run_sync(self, user_prompt: str, deps: Deps) -> Design:
        return self.agent.run_sync(user_prompt, deps=deps).output
