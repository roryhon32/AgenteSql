import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from promptinterpretador import prompt_interpretador
from promptsql import prompt_sql


load_dotenv()



modelo = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0
)



pergunta_usuario = input("O que você precisa saber? ")


# SCHEMA DO BANCO


tabela = "usuarios"

colunas = """
id
Cliente
idade
cidade
faturamento
data_cadastro
ultima_compra
"""

# AGENTE 1 — INTERPRETADOR


cadeia_interpretador = (
    prompt_interpretador
    | modelo
    | StrOutputParser()
)


interpretacao = cadeia_interpretador.invoke({
    "pergunta": pergunta_usuario,
    "tabela": tabela,
    "colunas": colunas
})


print("\n--- Interpretação ---")
print(interpretacao.strip())



# AGENTE 2 — TEXT-TO-SQL
cadeia_sql = (
    prompt_sql
    | modelo
    | StrOutputParser()
)


resposta_sql = cadeia_sql.invoke({
    "pergunta": pergunta_usuario,
    "interpretacao": interpretacao,
    "tabela": tabela,
    "colunas": colunas
})


print("\n--- SQL Gerado ---")
print(resposta_sql.strip())