from typing import Literal

from pydantic import BaseModel, Field

class State(BaseModel):
    """Atendimento de Prontuarios medicos"""
    
    paciente_id: str = Field(..., description="ID do paciente")
    prontuario: str = Field(..., description="Conteudo do prontuario medico")  
    # Preenchidos pelo no de atendimento (triagem): nao vem na entrada.
    urgencia: Literal["urgente", "nao_urgente"] | None = Field(None, description="Nivel de urgencia do atendimento")
    justificativa: str | None = Field(None, description="Motivo da classificacao de urgencia")
    data_atualizacao: str = Field(..., description="Data da ultima atualizacao do prontuario")

    