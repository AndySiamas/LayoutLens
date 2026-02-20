from typing import Literal

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from layout_lens.utilities.utilities import Utilities


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env')

    llm_base_url: str = 'http://localhost:1234/v1'
    llm_provider: Literal['local', 'openai', 'google', 'anthropic'] = 'local'
    llm_model: str = 'google/gemma-3-27b'
    llm_api_key: str = ''

    # Root folder where all runs go
    output_dir_path: Path = Path('./output')

    # Per-run folder (set at runtime)
    run_output_dir_path: Path = Path('./output')

    # Output files (set from run_output_dir_path)
    design_output_path: Path = Path('./output/design.json')
    space_output_path: Path = Path('./output/space.json')
    room_plan_output_path: Path = Path('./output/room_plan.json')
    validation_error_path: Path = Path('./output/validation_error.txt')

    def __init__(self, **data) -> None:
        Utilities.ensure_env_file(env_path=Path('.env'), example_path=Path('.env.example'))
        super().__init__(**data)
        self.set_run_output_dir(self.output_dir_path)

    def set_run_output_dir(self, run_dir: Path) -> None:
        self.run_output_dir_path = run_dir
        self.design_output_path = run_dir / 'design.json'
        self.space_output_path = run_dir / 'space.json'
        self.room_plan_output_path = run_dir / 'room_plan.json'
        self.validation_error_path = run_dir / 'validation_error.txt'