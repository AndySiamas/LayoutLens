from pydantic import BaseModel, ConfigDict


class StrictModel(BaseModel):
    """Strict schema contract: reject unknown keys (great for LLM outputs)."""
    model_config = ConfigDict(extra="forbid")
