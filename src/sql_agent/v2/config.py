"""
config.py — Configurações centralizadas via config.yaml + .env

Prioridade de leitura (menor para maior):
  1. Valores padrão hardcoded
  2. config.yaml na raiz do projeto
  3. Variáveis de ambiente (.env ou sistema)
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Localiza a raiz do projeto (4 níveis acima deste arquivo: v2/sql_agent/src/AgenteSQL)
_PROJECT_ROOT = Path(__file__).resolve().parents[4]
_CONFIG_FILE = _PROJECT_ROOT / "config.yaml"
_ENV_FILE = _PROJECT_ROOT / ".env"


def _load_yaml() -> dict:
    """Carrega config.yaml se existir, retornando dicionário vazio caso contrário."""
    if _CONFIG_FILE.exists():
        with open(_CONFIG_FILE, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


_yaml = _load_yaml()
_db = _yaml.get("database", {})
_llm = _yaml.get("llm", {})


class Settings(BaseSettings):
    """Configurações centralizadas lidas do .env com fallback para config.yaml."""

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Banco de Dados ---
    db_path: str = Field(default=_db.get("db_path", ":memory:"))
    max_rows_context: int = Field(default=_db.get("max_rows_context", 15))
    query_timeout: int = Field(default=_db.get("query_timeout", 30))

    # --- LLM ---
    llm_backend: Literal["ollama", "openai"] = Field(
        default=_llm.get("backend", "ollama")
    )
    ollama_model: str = Field(default=_llm.get("ollama_model", "qwen2.5-coder:7b"))
    ollama_base_url: str = Field(
        default=_llm.get("ollama_base_url", "http://localhost:11434")
    )
    openai_model: str = Field(default=_llm.get("openai_model", "gpt-4o-mini"))
    openai_api_key: str = Field(default="")
    temperature: float = Field(default=float(_llm.get("temperature", 0.0)))
    max_retries: int = Field(default=int(_llm.get("max_retries", 2)))


# Singleton exportado para uso em toda a aplicação
settings = Settings()
