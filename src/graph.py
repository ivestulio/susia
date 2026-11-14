"""Montagem do grafo: START -> atendimento -> (urgente | nao_urgente) -> END."""

from langgraph.graph import END, START, StateGraph

from src.edges.roteamento import rotear_por_urgencia
from src.nodes.atendimento import atendimento
from src.state import State

builder = StateGraph(State)

builder.add_node("atendimento", atendimento)

builder.add_edge(START, "atendimento")
builder.add_conditional_edges(
    "atendimento",
    rotear_por_urgencia,
    # Proxima etapa: "urgente" -> emergencia, "nao_urgente" -> clinico_geral.
    {"urgente": END, "nao_urgente": END},
)

grafo = builder.compile()
