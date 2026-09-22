"""Gerenciamento de configurações e variáveis de ambiente."""

import os
from dataclasses import dataclass
from dotenv import load_dotenv

# Carrega o .env a partir da raiz do projeto
load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Configurações centralizadas da aplicação."""

    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    temperature: float = 0.0

    def validate(self) -> None:
        """Verifica se as configurações mínimas necessárias estão presentes."""
        if not self.openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY não foi encontrada nas variáveis de ambiente.\n"
                "Por favor, configure sua chave no arquivo .env antes de executar."
            )


settings = Settings()

