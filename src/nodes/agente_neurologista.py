"""No agente_neurologista: parecer neurologico com apoio do RAG sobre o CID-10."""

from langchain.agents import create_agent
from pydantic import BaseModel, Field

from src.services.llm import modelo
from src.state import CidSugerido, ParecerNeurologico, State
from src.tools.cid10 import buscar_cid10

PROMPT_NEUROLOGISTA = """Voce e um medico neurologista avaliando um prontuario
encaminhado pela triagem.

1. Separe todos os sintomas e sinais clinicos descritos no prontuario.
2. Para cada um, chame a ferramenta buscar_cid10 (um sintoma por chamada), usando
   o termo medico (ex.: "disartria" em vez de "fala arrastada", "hemiparesia" em vez
   de "fraqueza no braco").
3. Para cada sintoma, escolha a categoria do CID-10 mais adequada entre as que a
   ferramenta devolveu, priorizando categorias neurologicas e cerebrovasculares
   (codigos G e I60 a I69) quando forem pertinentes.
4. Emita um parecer neurologico: hipotese diagnostica principal, nivel de risco
   neurologico imediato (alto, moderado ou baixo) e condutas e exames iniciais.
   Considere a classificacao de urgencia da triagem ao definir o risco e, em suspeita
   de AVC, o tempo desde o inicio dos sintomas.

Use somente codigos devolvidos pela ferramenta: nunca invente um codigo. Se nenhuma
categoria devolvida servir para um sintoma, nao sugira CID para ele."""


class ResultadoNeurologista(BaseModel):
    """Resultado do agente neurologista."""

    sintomas: list[str] = Field(description="Sintomas e sinais clinicos separados do prontuario")
    cids_sugeridos: list[CidSugerido] = Field(description="Categoria do CID-10 sugerida para cada sintoma")
    # Sem Field(description=...): em streaming a API exige schema estrito, e la um campo
    # que aponta para outro modelo ($ref) nao pode ter descricao propria. A descricao
    # vem da docstring de ParecerNeurologico.
    parecer: ParecerNeurologico


def agente_neurologista(state: State) -> dict:
    """Roda o agente com a ferramenta de RAG e devolve so os campos que altera no state."""
    agente = create_agent(
        modelo(),
        [buscar_cid10],
        system_prompt=PROMPT_NEUROLOGISTA,
        response_format=ResultadoNeurologista,
    )
    entrada = (
        f"Triagem: {state.urgencia} - {state.justificativa}\n\n"
        f"Prontuario:\n{state.prontuario}"
    )
    saida = agente.invoke({"messages": [("human", entrada)]})
    resultado: ResultadoNeurologista = saida["structured_response"]
    return {
        "sintomas": resultado.sintomas,
        "cids_sugeridos": resultado.cids_sugeridos,
        "parecer_neurologico": resultado.parecer,
    }
