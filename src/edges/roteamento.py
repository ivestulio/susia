"""Arestas condicionais: decidem o proximo passo a partir do state, sem chamar o LLM."""

from typing import Literal

from src.state import State


def rotear_triagem(state: State) -> Literal["cardiologico", "urgente", "nao_urgente"]:
    """Escolhe o ramo a partir da triagem.

    Casos cardiologicos vao para o cardiologista, mesmo quando urgentes.
    Sem classificacao, trata como urgente.
    """
    if state.especialidade == "cardiologia":
        return "cardiologico"
    return "nao_urgente" if state.urgencia == "nao_urgente" else "urgente"
