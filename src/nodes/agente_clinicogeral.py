"""No agente_clinicogeral: parecer de clinica geral com apoio do RAG sobre o CID-10."""

from langchain.agents import create_agent
from pydantic import BaseModel, Field

from src.services.llm import modelo
from src.state import CidSugerido, ParecerClinico, State
from src.tools.cid10 import buscar_cid10

PROMPT_CLINICO_GERAL = """Voce e um medico clinico geral, em atencao primaria, avaliando
um prontuario que a triagem classificou como nao urgente.

1. Separe os sintomas, sinais e queixas descritos no prontuario.
2. Para cada um, chame a ferramenta buscar_cid10 (um sintoma por chamada).
3. Para cada sintoma, escolha a categoria do CID-10 mais adequada entre as que a
   ferramenta devolveu.
4. Emita um parecer: hipotese diagnostica principal, orientacoes ao paciente,
   exames complementares (se houver indicacao) e acompanhamento ou prazo de retorno.

Se o prontuario nao tiver queixas (por exemplo, consulta de rotina ou renovacao de
receita), nao chame a ferramenta: devolva sintomas e CIDs vazios e descreva o motivo
da consulta na hipotese diagnostica.

Se identificar algum sinal de alarme, indique no retorno o encaminhamento necessario.

Use somente codigos devolvidos pela ferramenta: nunca invente um codigo. Se nenhuma
categoria devolvida servir para um sintoma, nao sugira CID para ele."""


class ResultadoClinicoGeral(BaseModel):
    """Resultado do agente clinico geral."""

    sintomas: list[str] = Field(description="Sintomas, sinais e queixas separados do prontuario")
    cids_sugeridos: list[CidSugerido] = Field(description="Categoria do CID-10 sugerida para cada sintoma")
    # Sem Field(description=...): em streaming a API exige schema estrito, e la um campo
    # que aponta para outro modelo ($ref) nao pode ter descricao propria. A descricao
    # vem da docstring de ParecerClinico.
    parecer: ParecerClinico


def agente_clinicogeral(state: State) -> dict:
    """Roda o agente com a ferramenta de RAG e devolve so os campos que altera no state."""
    agente = create_agent(
        modelo(),
        [buscar_cid10],
        system_prompt=PROMPT_CLINICO_GERAL,
        response_format=ResultadoClinicoGeral,
    )
    entrada = (
        f"Triagem: {state.urgencia} - {state.justificativa}\n\n"
        f"Prontuario:\n{state.prontuario}"
    )
    saida = agente.invoke({"messages": [("human", entrada)]})
    resultado: ResultadoClinicoGeral = saida["structured_response"]
    return {
        "sintomas": resultado.sintomas,
        "cids_sugeridos": resultado.cids_sugeridos,
        "parecer_clinico": resultado.parecer,
    }
