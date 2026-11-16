"""No de atendimento: faz a triagem do prontuario e classifica a urgencia."""

from typing import Literal # Para definir tipos literais como "urgente" e "nao_urgente"
from pydantic import BaseModel, Field # 
from src.services.llm import modelo
from src.state import State

PROMPT_TRIAGEM = """Voce e um profissional de triagem em um servico de saude.
Leia o prontuario e classifique o atendimento:

- "urgente": risco imediato a vida ou de agravamento rapido. Exemplos: dor toracica,
  falta de ar, rebaixamento de consciencia, sinais de AVC, sangramento ativo,
  sinais vitais instaveis, trauma grave, reacao alergica grave, dor intensa e subita.
- "nao_urgente": quadro estavel, queixas leves ou cronicas, rotina, renovacao de
  receita, acompanhamento.

Na duvida, classifique como "urgente".
Justifique em uma ou duas frases, citando os achados do prontuario."""

# Modelo de classificacao de urgencia do atendimento
class Classificacao(BaseModel):
    """Resultado da triagem."""

    urgencia: Literal["urgente", "nao_urgente"] = Field(description="Nivel de urgencia")
    justificativa: str = Field(description="Motivo da classificacao")


def atendimento(state: State) -> dict:
    """Classifica o prontuario e devolve so os campos que altera no state."""
    triador = modelo().with_structured_output(Classificacao)
    resultado = triador.invoke(
        [
            ("system", PROMPT_TRIAGEM),
            ("human", state.prontuario),
        ]
    )
    return {"urgencia": resultado.urgencia, "justificativa": resultado.justificativa}
