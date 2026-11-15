from typing import Literal

from pydantic import BaseModel, Field


class CidSugerido(BaseModel):
    """Categoria do CID-10 sugerida para um sintoma."""

    sintoma: str = Field(description="Sintoma ou sinal clinico do prontuario")
    codigo: str = Field(description="Codigo da categoria no CID-10, ex.: R07")
    descricao: str = Field(description="Descricao da categoria no CID-10")


class State(BaseModel):
    """Atendimento de Prontuarios medicos"""

    paciente_id: str = Field(..., description="ID do paciente")
    prontuario: str = Field(..., description="Conteudo do prontuario medico")
    # Preenchidos pelo no de atendimento (triagem): nao vem na entrada.
    urgencia: Literal["urgente", "nao_urgente"] | None = Field(None, description="Nivel de urgencia do atendimento")
    justificativa: str | None = Field(None, description="Motivo da classificacao de urgencia")
    # Preenchidos pelo no agente_urgencia: so quando o prontuario e urgente.
    sintomas: list[str] = Field(default_factory=list, description="Sintomas separados do prontuario")
    cids_sugeridos: list[CidSugerido] = Field(default_factory=list, description="Categorias do CID-10 sugeridas por sintoma")
    data_atualizacao: str = Field(..., description="Data da ultima atualizacao do prontuario")
