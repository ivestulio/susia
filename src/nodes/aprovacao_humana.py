"""No aprovacao_humana: pausa o fluxo para um profissional aprovar ou rejeitar o parecer.

Usa interrupt() do LangGraph: a execucao para, devolve o pacote de revisao e so
continua quando alguem responde com Command(resume=...). Isso exige um checkpointer
(o LangGraph Studio/servidor ja tem um; no Python, ver exemplo.py).

Resposta esperada:
    {"aprovado": true}
    {"aprovado": false, "motivo": "..."}          # motivo obrigatorio na rejeicao
    {"aprovado": true, "revisor": "Dra. Ana"}     # revisor opcional

Na retomada o no roda de novo desde o inicio: por isso, antes do interrupt, ele so le
o state (nada de chamar modelo ou gravar em lugar algum).
"""

import json

from langgraph.types import interrupt
from pydantic import ValidationError

from src.state import RevisaoHumana, State

INSTRUCAO = (
    'Responda {"aprovado": true} para aprovar ou '
    '{"aprovado": false, "motivo": "..."} para rejeitar.'
)


def _pacote_revisao(state: State) -> dict:
    """Dados que o revisor precisa ver para decidir."""
    pacote = {
        "paciente_id": state.paciente_id,
        "urgencia": state.urgencia,
        "especialidade": state.especialidade,
        "justificativa": state.justificativa,
        "sintomas": state.sintomas,
        "cids_sugeridos": [cid.model_dump() for cid in state.cids_sugeridos],
        "instrucao": INSTRUCAO,
    }
    for campo in ("parecer_cardiologico", "parecer_neurologico", "parecer_clinico"):
        parecer = getattr(state, campo)
        if parecer is not None:
            pacote[campo] = parecer.model_dump()
    return pacote


def aprovacao_humana(state: State) -> dict:
    """Pausa ate receber uma resposta valida e grava a decisao em `revisao`."""
    pacote = _pacote_revisao(state)
    while True:
        resposta = interrupt(pacote)
        if isinstance(resposta, str):
            # Alguns clientes mandam o JSON como texto.
            try:
                resposta = json.loads(resposta)
            except json.JSONDecodeError:
                pass
        try:
            revisao = RevisaoHumana.model_validate(resposta)
        except ValidationError as erro:
            # Resposta invalida: pede de novo, explicando o problema.
            mensagens = "; ".join(e["msg"] for e in erro.errors())
            pacote = {**pacote, "erro": f"Resposta invalida ({mensagens}). {INSTRUCAO}"}
            continue
        return {"revisao": revisao}
