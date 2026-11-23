"""Montagem do grafo.

START -> atendimento -> cardiologico -> agente_cardiologista -> END
                     -> urgente      -> agente_urgencia      -> END
                     -> nao_urgente  -> agente_clinicogeral  -> END
"""

from langgraph.graph import END, START, StateGraph

from src.edges.roteamento import rotear_triagem
from src.nodes.agente_cardiologista import agente_cardiologista
from src.nodes.agente_clinicogeral import agente_clinicogeral
from src.nodes.agente_urgencia import agente_urgencia
from src.nodes.atendimento import atendimento
from src.state import State

builder = StateGraph(State)

builder.add_node("atendimento", atendimento)
builder.add_node("agente_urgencia", agente_urgencia)
builder.add_node("agente_cardiologista", agente_cardiologista)
builder.add_node("agente_clinicogeral", agente_clinicogeral)

builder.add_edge(START, "atendimento")
builder.add_conditional_edges(
    "atendimento",
    rotear_triagem,
    {
        "cardiologico": "agente_cardiologista",
        "urgente": "agente_urgencia",
        "nao_urgente": "agente_clinicogeral",
    },
)
builder.add_edge("agente_urgencia", END)
builder.add_edge("agente_cardiologista", END)
builder.add_edge("agente_clinicogeral", END)

grafo = builder.compile()
