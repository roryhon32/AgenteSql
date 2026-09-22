"""Agente 1: Interpretador de regras de negócio e intenções."""

from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

from src.sql_agent.config.settings import settings
from src.sql_agent.database.schema import TableSchema
from src.sql_agent.prompts.interpreter_prompt import prompt_interpretador


class InterpreterAgent:
    """Interpreta perguntas em linguagem natural e traduz em especificações de negócio."""

    def __init__(self, llm: BaseChatModel = None) -> None:
        settings.validate()
        self.llm = llm or ChatOpenAI(
            model=settings.openai_model,
            temperature=settings.temperature,
            api_key=settings.openai_api_key
        )
        self.chain = prompt_interpretador | self.llm | StrOutputParser()

    def interpret(self, question: str, table_schema: TableSchema, history: str = "") -> str:
        """Executa a interpretação de negócio para a pergunta fornecida considerando o histórico."""
        response = self.chain.invoke({
            "pergunta": question,
            "tabela": table_schema.name,
            "colunas": table_schema.get_columns_text(),
            "historico": history or "Nenhum histórico anterior disponível."
        })
        return response.strip()

