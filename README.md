# Agente Text-to-SQL para DuckDB

Projeto estruturado seguindo boas práticas de Engenharia de Software e Clean Architecture para tradução de perguntas de negócio em consultas SQL seguras para DuckDB utilizando LangChain e modelos da OpenAI, com suporte a **Memória Conversacional Multi-Turn**.

---

## Estrutura do Projeto

```text
estudo/
├── .env.example               # Modelo das variáveis de ambiente
├── .gitignore                 # Proteção de credenciais (.env) e arquivos temporários
├── pyproject.toml             # Dependências e metadados do projeto
├── README.md                  # Documentação do projeto
├── main.py                    # Entrypoint CLI interativo para o usuário
│
├── src/
│   └── sql_agent/
│       ├── config/            # Configurações e validação de variáveis de ambiente
│       │   └── settings.py
│       ├── database/          # Schemas desacoplados e executor DuckDB
│       │   ├── schema.py
│       │   └── executor.py
│       ├── memory/            # Memória conversacional e controle de janela
│       │   └── conversation_memory.py
│       ├── prompts/           # Prompts especializados dos agentes
│       │   ├── interpreter_prompt.py
│       │   └── sql_prompt.py
│       ├── services/          # Agentes e orquestrador do pipeline
│       │   ├── interpreter_agent.py
│       │   ├── sql_generator_agent.py
│       │   └── orchestrator.py
│       └── utils/             # Validação de segurança (SQL read-only)
│           └── validators.py
│
├── examples/                  # Scripts e estudos preservados
│   ├── alura/
│   │   └── consultores.py
│   └── trip_planner.py
│
└── tests/                     # Testes unitários automatizados
    ├── test_memory.py
    ├── test_validator.py
    └── test_schema.py
```

---

## Configuração

1. Clone o repositório ou navegue até a pasta do projeto.
2. Copie o arquivo `.env.example` para `.env`:
   ```bash
   cp .env.example .env
   ```
3. Preencha sua chave da OpenAI no `.env`:
   ```env
   OPENAI_API_KEY="sk-proj-..."
   OPENAI_MODEL="gpt-4o-mini"
   ```

---

## Execução

Para iniciar o agente de forma interativa no terminal:

```bash
uv run python main.py
```

### Comandos Disponíveis no CLI:
- `sair` ou `exit`: Encerra o programa.
- `limpar` ou `reset`: Reinicia a memória da conversa para iniciar uma nova análise do zero.
- `historico`: Exibe os turnos e queries armazenados atualmente na memória.

### Exemplo de Diálogo Multi-Turn (Refinamento Contextual):
1. **Pergunta 1:** *"Quais clientes estão inativos?"*
   - Gera consulta com filtro de $\ge 180$ dias sem compra.
2. **Pergunta 2 (Refinamento):** *"E desses, quais são de São Paulo?"*
   - O agente mantém o filtro de inativos e adiciona `cidade = 'São Paulo'`.
3. **Pergunta 3 (Ordenação):** *"Ordene esses mesmos por faturamento decrescente"*
   - O agente mantém os filtros anteriores e acrescenta `ORDER BY faturamento DESC`.

---

## Executar os Testes Automatizados

Para rodar a suíte de testes unitários:

```bash
uv run python -m tests.test_memory
uv run python -m tests.test_validator
uv run python -m tests.test_schema
```

---

## Princípios de Engenharia Aplicados

- **Single Responsibility Principle (SRP):** Cada módulo tem uma responsabilidade única e bem definida.
- **Defesa em Profundidade (Defense in Depth):** O `SQLSecurityValidator` inspeciona a query gerada garantindo que seja estritamente `SELECT`/`WITH` e bloqueando injeções ou instruções destrutivas (`DROP`, `DELETE`, `UPDATE`, etc.).
- **Memória Conversacional com Sliding Window:** O componente `ConversationMemory` armazena turnos válidos em janela deslizante, permitindo referências contextuais e evitando saturação de tokens.
- **Guard Clauses:** Interrupção precoce caso o agente de interpretação não encontre regras adequadas para a pergunta.
- **Segurança de Credenciais:** O `.env` foi desindexado do Git e devidamente protegido pelo `.gitignore`.
