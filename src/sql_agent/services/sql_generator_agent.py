"""Agente 2: Gerador de consultas SQL DuckDB a partir da interpretação de negócio."""

from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

from src.sql_agent.config.settings import settings
from src.sql_agent.database.schema import TableSchema
from src.sql_agent.prompts.sql_prompt import prompt_sql


class SQLGeneratorAgent:
    """Traduz uma especificação de negócio em uma consulta SQL válida para DuckDB."""

    def __init__(self, llm: BaseChatModel = None) -> None:
        settings.validate()
        self.llm = llm or ChatOpenAI(
            model=settings.openai_model,
            temperature=settings.temperature,
            api_key=settings.openai_api_key
        )
        self.chain = prompt_sql | self.llm | StrOutputParser()

    def generate_sql(self, question: str, interpretation: str, table_schema: TableSchema, history: str = "") -> str:
        """Gera a instrução SQL com base na pergunta, interpretação estruturada e histórico recente."""
        response = self.chain.invoke({
            "pergunta": question,
            "interpretacao": interpretation,
            "tabela": table_schema.name,
            "colunas": table_schema.get_columns_text(),
            "historico": history or "Nenhum histórico anterior disponível."
        })
        return response.strip()

