"""
agent.py — Orquestrador do ciclo analítico completo.

Fluxo por pergunta:
  1. Geração SQL  → LLM recebe pergunta + schema dinâmico, retorna SQL puro
  2. Execução     → DatabaseManager valida e executa a query no DuckDB
  3. Self-healing → Se erro DuckDB, reenvia ao LLM com instrução de correção
                    (até max_retries tentativas)
  4. Síntese      → LLM analisa os dados retornados e responde em linguagem natural
  5. Zero rows    → Avisa o usuário sem chamar LLM na síntese

Backends suportados: Ollama (local) e OpenAI (API).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from src.sql_agent.memory.conversation_memory import ConversationMemory
from src.sql_agent.v2.config import Settings
from src.sql_agent.v2.database import DatabaseManager, ExecutionResult


# ---------------------------------------------------------------------------
# Modelo de resultado analítico
# ---------------------------------------------------------------------------

@dataclass
class AnalyticalResult:
    """Resultado completo de uma interação com o agente."""

    question: str
    sql: Optional[str]
    execution_result: Optional[ExecutionResult]
    analysis: str
    success: bool
    error: Optional[str] = None
    retries: int = 0


# ---------------------------------------------------------------------------
# Templates de Prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
Você é um agente analítico especializado em DuckDB e análise de dados de negócio.

Você tem acesso ao esquema do banco de dados abaixo (apenas a estrutura — sem registros reais):

{schema}

REGRAS OBRIGATÓRIAS:
- Gere SOMENTE consultas SELECT ou WITH ... SELECT.
- NUNCA gere INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE ou qualquer operação de escrita.
- Use SOMENTE tabelas e colunas presentes no esquema acima. Não invente colunas.
- Ao gerar SQL, responda APENAS com o SQL puro — sem explicações, sem blocos markdown, sem comentários.
- Use funções nativas do DuckDB: CURRENT_DATE, DATE_TRUNC(), DATE_DIFF(), INTERVAL, etc.
- Regras de negócio padrão:
    * Cliente ATIVO    → ultima_compra < 90 dias atrás
    * Cliente EM RISCO → ultima_compra entre 90 e 179 dias atrás
    * Cliente INATIVO  → ultima_compra >= 180 dias atrás
"""

_SQL_REQUEST = """\
Pergunta do usuário: {question}

Histórico recente da conversa:
{history}

Gere apenas a query SQL que responde à pergunta.
Responda diretamente com SELECT ou WITH — sem qualquer outra palavra.\
"""

_HEALING_REQUEST = """\
A query SQL gerou o seguinte erro no DuckDB:

Erro: {error}

Query com erro:
{sql}

Objetivo original: {question}

Corrija a query mantendo o objetivo. Responda APENAS com o SQL corrigido.\
"""

_SYNTHESIS_REQUEST = """\
A seguinte query foi executada no DuckDB em resposta à pergunta do usuário:

Pergunta: {question}

Query executada:
{sql}

Resultado ({shown} de {total} registros):
{table}

Analise esses dados e responda à pergunta em português, de forma clara e objetiva.
Destaque números relevantes, tendências ou anomalias.
Fale como um analista de dados conversando com uma área de negócio.\
"""


# ---------------------------------------------------------------------------
# Utilitários
# ---------------------------------------------------------------------------

def _extract_sql(text: str) -> str:
    """Remove blocos markdown (```sql ... ```) e retorna o SQL limpo."""
    text = text.strip()
    fence = re.search(r"```(?:sql)?\s*([\s\S]*?)```", text, re.IGNORECASE)
    if fence:
        return fence.group(1).strip()
    return text


def _build_llm(settings: Settings) -> BaseChatModel:
    """Instancia o LLM correto com base na configuração de backend."""
    if settings.llm_backend == "ollama":
        from langchain_ollama import ChatOllama  # type: ignore
        return ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=settings.temperature,
        )
    else:
        from langchain_openai import ChatOpenAI  # type: ignore
        return ChatOpenAI(
            model=settings.openai_model,
            temperature=settings.temperature,
            api_key=settings.openai_api_key,
        )


# ---------------------------------------------------------------------------
# Agente Analítico
# ---------------------------------------------------------------------------

class AnalyticalAgent:
    """
    Orquestra o ciclo completo: geração SQL → execução DuckDB → síntese LLM.

    Parâmetros:
        db       : instância do DatabaseManager já inicializada
        settings : configurações da aplicação
    """

    def __init__(self, db: DatabaseManager, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.llm = _build_llm(settings)
        self.memory = ConversationMemory()
        self._schema_cache: Optional[str] = None

    # ------------------------------------------------------------------
    # Schema dinâmico (cacheado após primeira leitura)
    # ------------------------------------------------------------------

    def get_schema(self) -> str:
        """Retorna o schema do banco, introspeccionando apenas uma vez por sessão."""
        if self._schema_cache is None:
            self._schema_cache = self.db.introspect_schema()
        return self._schema_cache

    def invalidate_schema_cache(self) -> None:
        """Força reintrospecção do schema na próxima chamada (útil após DDL externo)."""
        self._schema_cache = None

    # ------------------------------------------------------------------
    # Chamadas ao LLM
    # ------------------------------------------------------------------

    def _call_llm(self, messages: list) -> str:
        response: AIMessage = self.llm.invoke(messages)
        return response.content.strip()  # type: ignore[union-attr]

    def _generate_sql(self, question: str) -> str:
        """Etapa 1: pede ao LLM que gere a query SQL."""
        schema = self.get_schema()
        history = self.memory.get_history_text()

        messages = [
            SystemMessage(content=_SYSTEM_PROMPT.format(schema=schema)),
            HumanMessage(content=_SQL_REQUEST.format(
                question=question,
                history=history,
            )),
        ]
        raw = self._call_llm(messages)
        return _extract_sql(raw)

    def _heal_sql(self, question: str, bad_sql: str, error: str) -> str:
        """Etapa de auto-recuperação: reenvia o SQL com erro para o LLM corrigir."""
        schema = self.get_schema()
        messages = [
            SystemMessage(content=_SYSTEM_PROMPT.format(schema=schema)),
            HumanMessage(content=_HEALING_REQUEST.format(
                error=error,
                sql=bad_sql,
                question=question,
            )),
        ]
        raw = self._call_llm(messages)
        return _extract_sql(raw)

    def _synthesize(self, question: str, sql: str, result: ExecutionResult) -> str:
        """Etapa de síntese: o LLM analisa os dados e responde em linguagem natural."""
        table_md = self.db.format_as_markdown(result, self.settings.max_rows_context)
        messages = [
            SystemMessage(content="Você é um analista de dados sênior. Responda sempre em português."),
            HumanMessage(content=_SYNTHESIS_REQUEST.format(
                question=question,
                sql=sql,
                table=table_md,
                shown=min(result.row_count, self.settings.max_rows_context),
                total=result.row_count,
            )),
        ]
        return self._call_llm(messages)

    # ------------------------------------------------------------------
    # Pipeline principal
    # ------------------------------------------------------------------

    def process_query(self, question: str) -> AnalyticalResult:
        """
        Executa o pipeline completo para uma pergunta:
          Geração SQL → Execução segura → Auto-recuperação → Síntese analítica.
        """
        # ── Etapa 1: Geração do SQL ──────────────────────────────────────
        try:
            sql = self._generate_sql(question)
        except Exception as exc:
            return AnalyticalResult(
                question=question,
                sql=None,
                execution_result=None,
                analysis="",
                success=False,
                error=f"Erro ao gerar SQL via LLM: {exc}",
            )

        # ── Etapa 2: Execução com Self-Healing ───────────────────────────
        result: Optional[ExecutionResult] = None
        retries = 0

        while True:
            result = self.db.execute_safe(sql, timeout=self.settings.query_timeout)

            if result.success:
                break

            # Sem mais tentativas
            if retries >= self.settings.max_retries:
                return AnalyticalResult(
                    question=question,
                    sql=sql,
                    execution_result=result,
                    analysis="",
                    success=False,
                    error=(
                        f"Falha após {retries} tentativa(s) de correção automática.\n"
                        f"Último erro DuckDB: {result.error}"
                    ),
                    retries=retries,
                )

            # Tenta corrigir o SQL
            retries += 1
            try:
                sql = self._heal_sql(question, sql, result.error or "Erro desconhecido")
            except Exception as exc:
                return AnalyticalResult(
                    question=question,
                    sql=sql,
                    execution_result=result,
                    analysis="",
                    success=False,
                    error=f"Erro ao tentar corrigir o SQL (tentativa {retries}): {exc}",
                    retries=retries,
                )

        # ── Etapa 3: Zero rows ───────────────────────────────────────────
        if result.row_count == 0:
            self.memory.add_turn(question=question, interpretation="", sql=sql)
            return AnalyticalResult(
                question=question,
                sql=sql,
                execution_result=result,
                analysis="A consulta foi executada com sucesso, mas não retornou registros para os critérios informados.",
                success=True,
                retries=retries,
            )

        # ── Etapa 4: Síntese analítica ───────────────────────────────────
        try:
            analysis = self._synthesize(question, sql, result)
        except Exception as exc:
            # Síntese falhou, mas os dados foram recuperados — avisa sem perder os resultados
            analysis = f"[Análise indisponível: {exc}]"

        self.memory.add_turn(question=question, interpretation="", sql=sql)

        return AnalyticalResult(
            question=question,
            sql=sql,
            execution_result=result,
            analysis=analysis,
            success=True,
            retries=retries,
        )

    # ------------------------------------------------------------------
    # Controle de memória
    # ------------------------------------------------------------------

    def clear_memory(self) -> None:
        """Limpa o histórico conversacional."""
        self.memory.clear()

    @property
    def memory_turns_count(self) -> int:
        """Número de turnos na janela de memória atual."""
        return len(self.memory)
