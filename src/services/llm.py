"""Cliente do modelo. Unico ponto do projeto que sabe qual e o provedor."""

from functools import lru_cache # É um decorador nativo do Python que permite armazenar em cache o resultado de uma função. Isso evita recriar repetidamente o objeto que representa o cliente do LLM.
from pathlib import Path

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# Raiz do repositorio: o .env e encontrado independente de onde o programa e executado.
RAIZ = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=RAIZ / ".env", extra="ignore")

    # Azure OpenAI: endpoint e chave sao obrigatorios (sem default, falha cedo se faltarem)
    azure_openai_endpoint: str
    azure_openai_api_key: SecretStr
    azure_openai_api_version: str = "2024-10-21"
    azure_openai_chat_deployment: str = "gpt-4o"

    # OpenAI
    openai_api_key: SecretStr = SecretStr("")
    openai_model: str = "gpt-4o"

    # Gemini
    gemini_api_key: SecretStr = SecretStr("")
    gemini_model: str = "gemini-2.5-flash"

    # Azure AI Search: so consulta, o indice ja existe
    azure_search_endpoint: str = ""
    azure_search_index: str = "devflow-kb"
    azure_search_key: SecretStr = SecretStr("")

    # MLflow
    mlflow_tracking_uri: str = ""
    mlflow_experiment: str = "devflow"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """As configuracoes, lidas do ambiente/.env uma vez e reaproveitadas."""
    return Settings()


@lru_cache(maxsize=1)
def modelo() -> BaseChatModel:
    """O modelo de raciocinio, criado uma vez e reaproveitado."""
    settings = get_settings()
    # Microsoft Foundry, API v1 (.../openai/v1/): compativel com o cliente OpenAI padrao,
    # sem api-version. A Responses API e exigida pelos modelos gpt-5/codex, que tambem
    # nao aceitam temperature.
    return ChatOpenAI(
        base_url=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        model=settings.azure_openai_chat_deployment,
        use_responses_api=True,
    )
