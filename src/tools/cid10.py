"""Ferramenta de RAG sobre o CID-10, usada pelo agente de urgencia."""

from langchain_core.tools import tool

from src.services.cid10 import buscar


@tool
def buscar_cid10(sintoma: str) -> str:
    """Busca no CID-10 as categorias mais proximas de um sintoma ou sinal clinico.

    Use um sintoma por chamada, em linguagem medica (ex.: "dor toracica", "dispneia").
    Devolve uma lista de linhas no formato "codigo - descricao".
    """
    resultados = buscar(sintoma)
    return "\n".join(f"{r['codigo']} - {r['descricao']}" for r in resultados)
