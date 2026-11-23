"""Arestas condicionais: decidem o proximo passo a partir do state, sem chamar o LLM."""

from typing import Literal

from src.state import State


def rotear_guardrail(state: State) -> Literal["liberado", "bloqueado"]:
    """So segue para a triagem se o guardrail liberou. Sem resultado, bloqueia."""
    if state.guardrail is not None and not state.guardrail.bloqueado:
        return "liberado"
    return "bloqueado"


def rotear_triagem(
    state: State,
) -> Literal["cardiologico", "neurologico", "urgente", "nao_urgente"]:
    """Escolhe o ramo a partir da triagem.

    Casos de especialidade (cardiologia, neurologia) vao para o especialista, mesmo
    quando urgentes. Sem classificacao, trata como urgente.
    """
    if state.especialidade == "cardiologia":
        return "cardiologico"
    if state.especialidade == "neurologia":
        return "neurologico"
    return "nao_urgente" if state.urgencia == "nao_urgente" else "urgente"
