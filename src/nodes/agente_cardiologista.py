"""No agente_cardiologista: parecer cardiologico com apoio do RAG sobre o CID-10."""

from langchain.agents import create_agent
from pydantic import BaseModel, Field

from src.services.llm import modelo
from src.state import CidSugerido, ParecerCardiologico, State
from src.tools.cid10 import buscar_cid10

PROMPT_CARDIOLOGISTA = """Voce e um medico cardiologista avaliando um prontuario
encaminhado pela triagem.

1. Separe todos os sintomas e sinais clinicos descritos no prontuario.
2. Para cada um, chame a ferramenta buscar_cid10 (um sintoma por chamada).
3. Para cada sintoma, escolha a categoria do CID-10 mais adequada entre as que a
   ferramenta devolveu, priorizando categorias cardiovasculares (codigos I) quando
   forem pertinentes.
4. Emita um parecer cardiologico: hipotese diagnostica principal, nivel de risco
   cardiovascular imediato (alto, moderado ou baixo) e condutas e exames iniciais.
   Considere a classificacao de urgencia da triagem ao definir o risco.

Use somente codigos devolvidos pela ferramenta: nunca invente um codigo. Se nenhuma
categoria devolvida servir para um sintoma, nao sugira CID para ele."""


class ResultadoCardiologista(BaseModel):
    """Resultado do agente cardiologista."""

    sintomas: list[str] = Field(description="Sintomas e sinais clinicos separados do prontuario")
    cids_sugeridos: list[CidSugerido] = Field(description="Categoria do CID-10 sugerida para cada sintoma")
    # Sem Field(description=...): em streaming a API exige schema estrito, e la um campo
    # que aponta para outro modelo ($ref) nao pode ter descricao propria. A descricao
    # vem da docstring de ParecerCardiologico.
    parecer: ParecerCardiologico


def agente_cardiologista(state: State) -> dict:
    """Roda o agente com a ferramenta de RAG e devolve so os campos que altera no state."""
    agente = create_agent(
        modelo(),
        [buscar_cid10],
        system_prompt=PROMPT_CARDIOLOGISTA,
        response_format=ResultadoCardiologista,
    )
    entrada = (
        f"Triagem: {state.urgencia} - {state.justificativa}\n\n"
        f"Prontuario:\n{state.prontuario}"
    )
    saida = agente.invoke({"messages": [("human", entrada)]})
    resultado: ResultadoCardiologista = saida["structured_response"]
    return {
        "sintomas": resultado.sintomas,
        "cids_sugeridos": resultado.cids_sugeridos,
        "parecer_cardiologico": resultado.parecer,
    }
