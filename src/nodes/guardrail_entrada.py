"""No guardrail_entrada: primeira etapa do grafo, antes de qualquer chamada ao modelo."""

from src.services.guardrail import verificar_prontuario
from src.state import State


def guardrail_entrada(state: State) -> dict:
    """Mascara segredos e PII e bloqueia injecao de prompt.

    Substitui o prontuario no state pela versao sanitizada: os nos seguintes so veem o
    texto ja mascarado. Se bloqueado, o prontuario fica vazio e o grafo termina.
    """
    sanitizado, resultado = verificar_prontuario(state.prontuario)
    return {"prontuario": sanitizado, "guardrail": resultado}
