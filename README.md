<div align="center">

# AgenteSQL

**Agente inteligente de Text-to-SQL com arquitetura multi-agente, memória conversacional e execução em DuckDB**

[![Python](https://img.shields.io/badge/Python-3.13+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![LangChain](https://img.shields.io/badge/LangChain-0.3-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white)](https://www.langchain.com/)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o-412991?style=for-the-badge&logo=openai&logoColor=white)](https://openai.com/)
[![DuckDB](https://img.shields.io/badge/DuckDB-1.5-FFF000?style=for-the-badge&logo=duckdb&logoColor=black)](https://duckdb.org/)

Transforme perguntas em linguagem natural em consultas SQL otimizadas para DuckDB — com interpretação de regras de negócio, validação de segurança e execução interativa dos resultados.

</div>

---

## Sobre o Projeto

O **AgenteSQL** é um sistema multi-agente que converte perguntas em português, escritas em linguagem natural, em consultas SQL válidas para [DuckDB](https://duckdb.org/).

O pipeline é composto por dois agentes especializados que trabalham em sequência:

1. **Agente Interpretador** — Um analista de negócio que transforma a pergunta do usuário em uma especificação analítica estruturada.
2. **Agente SQL** — Um especialista em DuckDB que traduz essa especificação em uma consulta SQL válida e segura.

Além disso, o sistema conta com memória conversacional (sliding window), validação de segurança em profundidade (permitindo apenas `SELECT`/`WITH`) e execução interativa dos resultados diretamente no DuckDB.

---

## Tecnologias

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![LangChain](https://img.shields.io/badge/LangChain-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=for-the-badge&logo=openai&logoColor=white)
![DuckDB](https://img.shields.io/badge/DuckDB-FFF000?style=for-the-badge&logo=duckdb&logoColor=black)

| Pacote | Versão | Função |
|--------|--------|--------|
| `langchain` | 0.3.x | Framework de orquestração de agentes LLM |
| `langchain-openai` | 0.3.x | Integração com modelos OpenAI |
| `duckdb` | 1.5.x | Engine SQL analítico para execução de queries |
| `python-dotenv` | 1.1.x | Gerenciamento de variáveis de ambiente |

---

## Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                        USUÁRIO                               │
│              "Quais clientes estão inativos?"                │
└──────────────────────────┬────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    ORQUESTRADOR                              │
│              SQLAgentOrchestrator                            │
│         (memória conversacional + catálogo)                  │
└──────┬──────────────────────────────────────┬─────────────────┘
       │                                      │
       ▼                                      │
┌──────────────────────┐                      │
│  AGENTE 1             │                     │
│  Interpretador de     │                     │
│  Negócio              │                     │
│                       │                     │
│  • Regras de negócio  │                     │
│  • Métricas           │                     │
│  • Filtros            │                     │
│  • Granularidade      │                     │
└──────────┬────────────┘                     │
           │ Especificação                    │
           │ Analítica                        │
           ▼                                  │
┌──────────────────────┐                      │
│  AGENTE 2             │                     │
│  Gerador SQL DuckDB   │                     │
│                       │                     │
│  • CTEs               │                     │
│  • Funções DuckDB     │                     │
│  • SQL Read-Only      │                     │
└──────────┬────────────┘                     │
           │ SQL Bruto                        │
           ▼                                  │
┌──────────────────────┐                      │
│  VALIDADOR            │                     │
│  SQLSecurityValidator │                     │
│                       │                     │
│  • Apenas SELECT/WITH │                     │
│  • Sem múltiplos stmt │                     │
│  • Keywords proibidas │                     │
└──────────┬────────────┘                     │
           │ SQL Validado                     │
           ▼                                  ▼
┌──────────────────────┐       ┌──────────────────────┐
│  MEMÓRIA              │       │  EXECUTOR             │
│  ConversationMemory   │       │  DuckDBExecutor       │
│                       │       │                       │
│  • Sliding window     │       │  • In-memory DB       │
│  • 5 turnos           │       │  • Dados de exemplo   │
│  • Histórico p/LLM    │       │  • Execução segura    │
└───────────────────────┘       └──────────┬────────────┘
                                            │
                                            ▼
                                 ┌──────────────────────┐
                                 │  RESULTADOS           │
                                 │  Tabela formatada     │
                                 └──────────────────────┘
```

---

## Funcionalidades

### Interpretação Inteligente de Negócio
- Entende linguagem comercial informal ("quem parou de comprar?", "onde estamos perdendo margem?")
- Aplica regras de negócio automaticamente (cliente ativo, inativo, em risco)
- Suporta mais de 20 tipos de análise: cohort, retenção, ranking, evolução temporal, entre outros

### Geração de SQL Segura
- Gera apenas consultas read-only (`SELECT` / `WITH ... SELECT`)
- Validação em profundidade contra mais de 20 keywords proibidas (INSERT, DROP, DELETE, etc.)
- Proteção contra múltiplas instruções (SQL injection)
- Limpeza automática de formatação markdown do LLM

### Memória Conversacional
- Sliding window de 5 turnos para manter contexto entre perguntas
- Permite perguntas de follow-up como "e agora filtre só por São Paulo"
- Comandos para visualizar e limpar o histórico

### Execução Interativa no DuckDB
- Após gerar a query, o usuário pode escolher executá-la no DuckDB
- Banco em memória com dados de exemplo pré-carregados
- Resultados formatados em tabela com colunas alinhadas

### Segurança em Profundidade
- Prompt engineering com restrições rígidas
- Validação pós-geração no código Python
- Apenas operações de leitura permitidas

---

## Início Rápido

### Pré-requisitos

- Python 3.13+
- Chave de API da OpenAI

### Instalação

```bash
# Clone o repositório
git clone https://github.com/roryhon32/AgenteSql.git
cd AgenteSql

# Crie e ative o ambiente virtual
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/macOS
source .venv/bin/activate

# Instale as dependências
pip install langchain langchain-openai duckdb python-dotenv

# Configure a chave da OpenAI
echo "OPENAI_API_KEY=sk-sua-chave-aqui" > .env
```

### Variáveis de Ambiente

Crie um arquivo `.env` na raiz do projeto:

```env
OPENAI_API_KEY=sk-sua-chave-aqui
OPENAI_MODEL=gpt-4o-mini
```

---

## Como Usar

### CLI Interativa

```bash
python main.py
```

### Exemplo de Interação

```
=================================================================
           AGENTE TEXT-TO-SQL (DUCKDB)
=================================================================
Modelo LLM : gpt-4o-mini
Comandos:
  • 'sair'      - Encerrar o agente
  • 'limpar'    - Reiniciar memória/histórico da conversa
  • 'historico' - Exibir histórico de interações na memória

Após gerar uma query, você poderá escolher executá-la no DuckDB.
-----------------------------------------------------------------

O que você precisa saber? Quais clientes estão inativos?

Processando com os agentes de IA (considerando contexto)...

----------------------------------------
1. INTERPRETAÇÃO DE NEGÓCIO:
----------------------------------------
TIPO DE ANÁLISE: ANÁLISE DE CLIENTES, CHURN
INTENÇÃO: Identificar clientes cuja última compra ocorreu há 180+ dias
MÉTRICA: Faturamento (para priorização)
...

----------------------------------------
2. SQL DUCKDB GERADO:
----------------------------------------
SELECT Cliente, faturamento, ultima_compra
FROM usuarios
WHERE ultima_compra <= CURRENT_DATE - INTERVAL '180 days'
ORDER BY faturamento DESC

[Status: Consulta validada com sucesso - Apenas Leitura]

========================================
Deseja executar essa query no DuckDB? (s/n): s

Executando no DuckDB...

----------------------------------------
3. RESULTADOS DUCKDB:
----------------------------------------
Cliente          | faturamento | ultima_compra
-------------------------------------------------
Fernando Castro  | 34200.0     | 2026-02-24
Carlos Silva     | 12500.5     | 2026-03-06

Total: 2 registro(s) retornado(s).
```

### Comandos Disponíveis

| Comando | Ação |
|---------|------|
| `sair` / `exit` / `quit` | Encerrar o agente |
| `limpar` / `clear` / `reset` | Reiniciar memória da conversa |
| `historico` / `history` | Exibir histórico de interações |

---

## Estrutura do Projeto

```
AgenteSQL/
├── main.py                              # CLI interativa principal
├── requirements.txt                     # Dependências do projeto
├── .env                                 # Variáveis de ambiente (não versionado)
├── .gitignore
│
├── src/
│   └── sql_agent/
│       ├── __init__.py                  # Exports do pacote
│       ├── config/
│       │   └── settings.py              # Configurações centralizadas
│       ├── database/
│       │   ├── schema.py                # Catálogo de schemas e metadados
│       │   └── executor.py              # Executor seguro DuckDB
│       ├── memory/
│       │   └── conversation_memory.py   # Memória conversacional
│       ├── prompts/
│       │   ├── interpreter_prompt.py    # Prompt do Agente Interpretador
│       │   └── sql_prompt.py            # Prompt do Agente SQL
│       ├── services/
│       │   ├── orchestrator.py          # Orquestrador do pipeline
│       │   ├── interpreter_agent.py     # Agente 1: Interpretador de Negócio
│       │   └── sql_generator_agent.py   # Agente 2: Gerador SQL
│       └── utils/
│           └── validators.py            # Validador de segurança SQL
│
└── tests/
    ├── test_schema.py
    ├── test_memory.py
    └── test_validator.py
```

---

## Dados de Exemplo

O executor DuckDB cria automaticamente uma tabela `usuarios` com dados de exemplo:

| id | Cliente | idade | cidade | faturamento | data_cadastro | ultima_compra |
|----|---------|-------|--------|-------------|----------------|----------------|
| 1 | Carlos Silva | 42 | São Paulo | 12.500,50 | 2023-01-15 | ~200 dias atrás |
| 2 | Mariana Souza | 31 | Rio de Janeiro | 8.900,00 | 2023-03-10 | ~120 dias atrás |
| 3 | Fernando Castro | 55 | Belo Horizonte | 34.200,00 | 2022-11-05 | ~210 dias atrás |
| 4 | Beatriz Lima | 28 | Curitiba | 5.400,00 | 2024-02-01 | ~30 dias atrás |
| 5 | Lucas Oliveira | 39 | Porto Alegre | 19.800,75 | 2023-08-20 | ~95 dias atrás |
| 6 | Juliana Mendes | 47 | Salvador | 27.600,00 | 2022-07-14 | ~45 dias atrás |

### Regras de Negócio Embutidas

| Classificação | Regra |
|---------------|-------|
| **Ativo** | Última compra há menos de 90 dias |
| **Em Risco** | Última compra entre 90 e 179 dias |
| **Inativo** | Última compra há 180 dias ou mais |

---

## Testes

```bash
# Executar todos os testes
python -m pytest tests/ -v

# Testes individuais
python tests/test_schema.py
python tests/test_validator.py
python tests/test_memory.py
```

---

## Roadmap

- [ ] Suporte a múltiplas tabelas e JOINs
- [ ] Integração com arquivos CSV/Parquet via DuckDB
- [ ] Interface web com Streamlit
- [ ] Suporte a outros LLMs (Gemini, Claude, Llama)
- [ ] Export de resultados para Excel/CSV
- [ ] Gráficos automáticos com Plotly/Matplotlib

---

## Contribuindo

Contribuições são bem-vindas. Sinta-se à vontade para abrir issues e pull requests.

1. Fork o projeto
2. Crie sua branch (`git checkout -b feature/nova-funcionalidade`)
3. Commit suas mudanças (`git commit -m 'feat: nova funcionalidade'`)
4. Push para a branch (`git push origin feature/nova-funcionalidade`)
5. Abra um Pull Request

---

## Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.
