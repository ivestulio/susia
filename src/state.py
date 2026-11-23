from typing import Literal

from pydantic import BaseModel, Field


class CidSugerido(BaseModel):
    """Categoria do CID-10 sugerida para um sintoma."""

    sintoma: str = Field(description="Sintoma ou sinal clinico do prontuario")
    codigo: str = Field(description="Codigo da categoria no CID-10, ex.: R07")
    descricao: str = Field(description="Descricao da categoria no CID-10")


class ParecerCardiologico(BaseModel):
    """Parecer emitido pelo agente cardiologista."""

    hipotese_diagnostica: str = Field(description="Hipotese diagnostica cardiologica principal")
    risco: Literal["alto", "moderado", "baixo"] = Field(description="Nivel de risco cardiovascular imediato")
    condutas: list[str] = Field(description="Condutas e exames iniciais sugeridos, ex.: ECG, troponina")


class ParecerNeurologico(BaseModel):
    """Parecer emitido pelo agente neurologista."""

    hipotese_diagnostica: str = Field(description="Hipotese diagnostica neurologica principal")
    risco: Literal["alto", "moderado", "baixo"] = Field(description="Nivel de risco neurologico imediato")
    condutas: list[str] = Field(description="Condutas e exames iniciais sugeridos, ex.: TC de cranio, glicemia capilar")


class ParecerClinico(BaseModel):
    """Parecer emitido pelo agente clinico geral."""

    hipotese_diagnostica: str = Field(description="Hipotese diagnostica principal, ou motivo da consulta se nao houver queixa")
    orientacoes: list[str] = Field(description="Orientacoes ao paciente e medidas gerais")
    exames: list[str] = Field(description="Exames complementares sugeridos; vazia se nao houver")
    retorno: str = Field(description="Acompanhamento e prazo de retorno, ou encaminhamento a especialista")


class State(BaseModel):
    """Atendimento de Prontuarios medicos"""

    paciente_id: str = Field(..., description="ID do paciente")
    prontuario: str = Field(..., description="Conteudo do prontuario medico")
    # Preenchidos pelo no de atendimento (triagem): nao vem na entrada.
    urgencia: Literal["urgente", "nao_urgente"] | None = Field(None, description="Nivel de urgencia do atendimento")
    justificativa: str | None = Field(None, description="Motivo da classificacao de urgencia")
    especialidade: Literal["cardiologia", "neurologia", "geral"] | None = Field(None, description="Especialidade indicada pela triagem")
    # Preenchidos pelo agente que atender o caso (urgencia, cardiologista, neurologista ou clinico geral).
    sintomas: list[str] = Field(default_factory=list, description="Sintomas separados do prontuario")
    cids_sugeridos: list[CidSugerido] = Field(default_factory=list, description="Categorias do CID-10 sugeridas por sintoma")
    # Preenchido pelo agente_cardiologista: so quando a triagem indica cardiologia.
    parecer_cardiologico: ParecerCardiologico | None = Field(None, description="Parecer do cardiologista")
    # Preenchido pelo agente_neurologista: so quando a triagem indica neurologia.
    parecer_neurologico: ParecerNeurologico | None = Field(None, description="Parecer do neurologista")
    # Preenchido pelo agente_clinicogeral: so quando o caso nao e urgente nem de especialidade.
    parecer_clinico: ParecerClinico | None = Field(None, description="Parecer do clinico geral")
    data_atualizacao: str = Field(..., description="Data da ultima atualizacao do prontuario")
