from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env')
    llm_base_url: str = 'http://localhost:1234/v1'
    llm_model: str = 'qwen/qwen3-32b'
    room_grid_size: float = 0.25
    runs_dir_path: Path = Path('./runs')
    design_output_path: Path = runs_dir_path / Path('design.json')
    space_output_path: Path = runs_dir_path / Path('space.json')
    room_plan_output_path: Path = runs_dir_path / Path('room_plan.json')
    validation_error_path: Path = runs_dir_path / Path('validation_error.txt')
