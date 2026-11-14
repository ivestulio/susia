"""Arestas condicionais: decidem o proximo passo a partir do state, sem chamar o LLM."""

from typing import Literal

from src.state import State


def rotear_por_urgencia(state: State) -> Literal["urgente", "nao_urgente"]:
    """Segue o ramo definido pelo atendimento. Sem classificacao, trata como urgente."""
    return "nao_urgente" if state.urgencia == "nao_urgente" else "urgente"
