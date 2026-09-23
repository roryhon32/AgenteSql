"""
database.py — Gerenciamento de conexão DuckDB, introspecção de schema e execução segura.

Responsabilidades:
  - Abrir e manter conexão com DuckDB (in-memory ou arquivo)
  - Popular dados de exemplo em banco vazio
  - Introspectar schema dinamicamente via information_schema
  - Executar queries com validação de segurança e timeout
  - Formatar resultados como tabela Markdown
"""

from __future__ import annotations

import re
import threading
from dataclasses import dataclass, field
from typing import Optional

import duckdb


# ---------------------------------------------------------------------------
# Modelo de resultado de execução
# ---------------------------------------------------------------------------

@dataclass
class ExecutionResult:
    """Resultado de uma execução de query no DuckDB."""

    success: bool
    columns: list[str] = field(default_factory=list)
    rows: list[tuple] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def row_count(self) -> int:
        return len(self.rows)


# ---------------------------------------------------------------------------
# Validação de segurança
# ---------------------------------------------------------------------------

_FORBIDDEN_RE = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|REPLACE|MERGE"
    r"|GRANT|REVOKE|ATTACH|DETACH|COPY|EXPORT|IMPORT|EXEC|EXECUTE"
    r"|PRAGMA|CALL|LOAD|INSTALL)\b",
    re.IGNORECASE,
)

_ALLOWED_START_RE = re.compile(r"^\s*(SELECT|WITH)\b", re.IGNORECASE)


def _validate_sql(sql: str) -> Optional[str]:
    """
    Retorna mensagem de erro se o SQL não for seguro, ou None se for válido.
    """
    stripped = sql.strip().rstrip(";").strip()

    if not stripped:
        return "A query está vazia."

    if not _ALLOWED_START_RE.match(stripped):
        first = re.match(r"\s*(\w+)", stripped)
        word = first.group(1) if first else "?"
        return f"A query deve começar com SELECT ou WITH. Recebido: '{word}'."

    match = _FORBIDDEN_RE.search(stripped)
    if match:
        return f"Operação proibida detectada: '{match.group(1).upper()}'. Apenas leitura é permitida."

    # Múltiplos statements
    body = stripped.rstrip(";")
    if ";" in body:
        return "Múltiplas instruções SQL detectadas (';' interno). Apenas uma query por vez."

    return None


# ---------------------------------------------------------------------------
# DatabaseManager
# ---------------------------------------------------------------------------

class DatabaseManager:
    """Gerencia a conexão DuckDB e fornece introspecção de schema e execução segura."""

    def __init__(self, db_path: str = ":memory:", auto_seed: bool = True) -> None:
        self.db_path = db_path
        self._conn = duckdb.connect(db_path)

        if auto_seed and db_path == ":memory:":
            self._seed_sample_data()

    # ------------------------------------------------------------------
    # Dados de exemplo
    # ------------------------------------------------------------------

    def _seed_sample_data(self) -> None:
        """Cria e popula a tabela de exemplo 'usuarios' em bancos in-memory vazios."""
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id            INTEGER PRIMARY KEY,
                Cliente       VARCHAR,
                idade         INTEGER,
                cidade        VARCHAR,
                faturamento   DOUBLE,
                data_cadastro DATE,
                ultima_compra DATE
            )
        """)
        count = self._conn.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]
        if count == 0:
            self._conn.execute("""
                INSERT INTO usuarios VALUES
                (1, 'Carlos Silva',    42, 'São Paulo',       12500.50, '2023-01-15', CURRENT_DATE - INTERVAL '200 days'),
                (2, 'Mariana Souza',   31, 'Rio de Janeiro',   8900.00, '2023-03-10', CURRENT_DATE - INTERVAL '120 days'),
                (3, 'Fernando Castro', 55, 'Belo Horizonte',  34200.00, '2022-11-05', CURRENT_DATE - INTERVAL '210 days'),
                (4, 'Beatriz Lima',    28, 'Curitiba',         5400.00, '2024-02-01', CURRENT_DATE - INTERVAL '30 days'),
                (5, 'Lucas Oliveira',  39, 'Porto Alegre',    19800.75, '2023-08-20', CURRENT_DATE - INTERVAL '95 days'),
                (6, 'Juliana Mendes',  47, 'Salvador',        27600.00, '2022-07-14', CURRENT_DATE - INTERVAL '45 days')
            """)

    # ------------------------------------------------------------------
    # Introspecção de schema
    # ------------------------------------------------------------------

    def introspect_schema(self) -> str:
        """
        Inspeciona o banco em tempo de execução e retorna o schema como texto
        compacto pronto para injeção no System Prompt do LLM.
        """
        tables: list[tuple] = self._conn.execute("""
            SELECT DISTINCT table_name
            FROM information_schema.columns
            WHERE table_schema = 'main'
            ORDER BY table_name
        """).fetchall()

        if not tables:
            return "(Nenhuma tabela encontrada no banco de dados.)"

        parts: list[str] = []
        for (table_name,) in tables:
            cols: list[tuple] = self._conn.execute("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = 'main'
                  AND table_name   = ?
                ORDER BY ordinal_position
            """, [table_name]).fetchall()

            col_lines = [f"  {col} {dtype}" for col, dtype in cols]
            parts.append(f"TABLE {table_name}:\n" + "\n".join(col_lines))

        return "\n\n".join(parts)

    # ------------------------------------------------------------------
    # Execução segura
    # ------------------------------------------------------------------

    def execute_safe(self, sql: str, timeout: int = 30) -> ExecutionResult:
        """
        Valida e executa uma query SQL de forma segura.

        - Rejeita comandos de escrita/mutação.
        - Executa em thread separada com timeout.
        - Retorna ExecutionResult com sucesso ou mensagem de erro.
        """
        # 1. Validação de segurança
        error_msg = _validate_sql(sql)
        if error_msg:
            return ExecutionResult(success=False, error=error_msg)

        cleaned = sql.strip().rstrip(";").strip()

        # 2. Execução com timeout via thread
        result_holder: list[Optional[tuple]] = [None]
        error_holder: list[Optional[str]] = [None]

        def _run() -> None:
            try:
                cursor = self._conn.execute(cleaned)
                cols = [desc[0] for desc in cursor.description] if cursor.description else []
                rows = cursor.fetchall()
                result_holder[0] = (cols, rows)
            except Exception as exc:
                error_holder[0] = str(exc)

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        thread.join(timeout=timeout)

        if thread.is_alive():
            return ExecutionResult(
                success=False,
                error=f"Timeout: a query excedeu {timeout}s de execução.",
            )

        if error_holder[0] is not None:
            return ExecutionResult(success=False, error=error_holder[0])

        cols, rows = result_holder[0]  # type: ignore[misc]
        return ExecutionResult(success=True, columns=cols, rows=rows)

    # ------------------------------------------------------------------
    # Formatação de resultados
    # ------------------------------------------------------------------

    @staticmethod
    def format_as_markdown(result: ExecutionResult, max_rows: int = 15) -> str:
        """Converte o resultado de uma query em tabela Markdown."""
        if not result.success or not result.columns:
            return ""

        rows = result.rows[:max_rows]

        header = "| " + " | ".join(result.columns) + " |"
        separator = "| " + " | ".join(["---"] * len(result.columns)) + " |"
        data_lines = [
            "| " + " | ".join(str(v) for v in row) + " |"
            for row in rows
        ]

        table = "\n".join([header, separator, *data_lines])

        if result.row_count > max_rows:
            table += f"\n\n_(Mostrando {max_rows} de {result.row_count} registros)_"

        return table

    # ------------------------------------------------------------------
    # Ciclo de vida
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Fecha a conexão com o DuckDB."""
        self._conn.close()
