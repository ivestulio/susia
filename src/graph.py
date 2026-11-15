"""Montagem do grafo.

START -> atendimento -> urgente      -> agente_urgencia -> END
                     -> nao_urgente  -> END
"""

from langgraph.graph import END, START, StateGraph

from src.edges.roteamento import rotear_por_urgencia
from src.nodes.agente_urgencia import agente_urgencia
from src.nodes.atendimento import atendimento
from src.state import State

builder = StateGraph(State)

builder.add_node("atendimento", atendimento)
builder.add_node("agente_urgencia", agente_urgencia)

builder.add_edge(START, "atendimento")
builder.add_conditional_edges(
    "atendimento",
    rotear_por_urgencia,
    {"urgente": "agente_urgencia", "nao_urgente": END},
)
builder.add_edge("agente_urgencia", END)

grafo = builder.compile()
