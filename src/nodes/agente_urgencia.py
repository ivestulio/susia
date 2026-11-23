"""No agente_urgencia: separa os sintomas do prontuario e consulta o CID-10 via RAG."""

from langchain.agents import create_agent
from pydantic import BaseModel, Field

from src.services.llm import modelo
from src.state import CidSugerido, State
from src.tools.cid10 import buscar_cid10

PROMPT_URGENCIA = """Voce e um medico emergencista analisando um prontuario urgente.

1. Separe todos os sintomas e sinais clinicos descritos no prontuario.
2. Para cada um, chame a ferramenta buscar_cid10 (um sintoma por chamada).
3. Para cada sintoma, escolha a categoria do CID-10 mais adequada entre as que a
   ferramenta devolveu.

Use somente codigos devolvidos pela ferramenta: nunca invente um codigo. Se nenhuma
categoria devolvida servir para um sintoma, nao sugira CID para ele."""


class ResultadoUrgencia(BaseModel):
    """Resultado do agente de urgencia."""

    sintomas: list[str] = Field(description="Sintomas e sinais clinicos separados do prontuario")
    cids_sugeridos: list[CidSugerido] = Field(description="Categoria do CID-10 sugerida para cada sintoma")


def agente_urgencia(state: State) -> dict:
    """Roda o agente com a ferramenta de RAG e devolve so os campos que altera no state."""
    agente = create_agent(
        modelo(),
        [buscar_cid10],
        system_prompt=PROMPT_URGENCIA,
        response_format=ResultadoUrgencia,
    )
    saida = agente.invoke({"messages": [("human", state.prontuario)]})
    resultado: ResultadoUrgencia = saida["structured_response"]
    return {"sintomas": resultado.sintomas, "cids_sugeridos": resultado.cids_sugeridos}
