from pydantic_ai.models import Model
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.providers.anthropic import AnthropicProvider

from layout_lens.core.settings import Settings


class ModelFactory:
    @staticmethod
    def create_model(settings: Settings) -> Model:
        provider: str = settings.llm_provider.strip().lower()
        match provider:
            case "local":
                return ModelFactory.create_openai_model(settings=settings)
            case "openai":
                return ModelFactory.create_openai_model(settings=settings)
            case "google":
                return ModelFactory.create_google_model(settings=settings)
            case "anthropic":
                return ModelFactory.create_anthropic_model(settings=settings)
            case _:
                raise ValueError(f"Unknown LLM_PROVIDER: {provider}")

    @staticmethod
    def create_openai_model(settings: Settings) -> Model:
        base_url_text: str = settings.llm_base_url.strip()
        api_key: str | None = settings.llm_api_key.strip() if settings.llm_api_key else 'api-key-not-set'
        provider: OpenAIProvider = OpenAIProvider(base_url=base_url_text, api_key=api_key)
        model: OpenAIChatModel = OpenAIChatModel(model_name=settings.llm_model, provider=provider)
        return model

    @staticmethod
    def create_google_model(settings: Settings) -> Model:
        api_key: str | None = settings.llm_api_key.strip() if settings.llm_api_key else None

        if api_key is None:
            raise ValueError("LLM_API_KEY is required when LLM_PROVIDER=google.")

        provider: GoogleProvider = GoogleProvider(api_key=api_key)
        model: GoogleModel = GoogleModel(settings.llm_model, provider=provider) 
        return model
    
    @staticmethod
    def create_anthropic_model(settings: Settings) -> Model:
        api_key: str | None = settings.llm_api_key.strip() if settings.llm_api_key else None

        if api_key is None:
            raise ValueError("LLM_API_KEY is required when LLM_PROVIDER=anthropic.")

        provider: AnthropicProvider = AnthropicProvider(api_key=api_key)
        model: AnthropicModel = AnthropicModel(settings.llm_model, provider=provider)
        return model