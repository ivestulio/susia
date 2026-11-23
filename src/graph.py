"""Montagem do grafo.

START -> guardrail_entrada -> bloqueado -> END
                          -> liberado  -> atendimento

atendimento -> cardiologico -> agente_cardiologista -> aprovacao_humana -> END
            -> neurologico  -> agente_neurologista  -> aprovacao_humana -> END
            -> urgente      -> agente_urgencia      -> aprovacao_humana -> END
            -> nao_urgente  -> agente_clinicogeral  -> aprovacao_humana -> END

aprovacao_humana pausa o fluxo (interrupt) ate um profissional aprovar ou rejeitar.
O grafo e compilado sem checkpointer: o LangGraph Studio/servidor fornece o dele.
Para rodar no Python, compile `builder` com um checkpointer (ver exemplo.py).
"""

from langgraph.graph import END, START, StateGraph

from src.edges.roteamento import rotear_guardrail, rotear_triagem
from src.nodes.agente_cardiologista import agente_cardiologista
from src.nodes.agente_clinicogeral import agente_clinicogeral
from src.nodes.agente_neurologista import agente_neurologista
from src.nodes.agente_urgencia import agente_urgencia
from src.nodes.aprovacao_humana import aprovacao_humana
from src.nodes.atendimento import atendimento
from src.nodes.guardrail_entrada import guardrail_entrada
from src.state import State

builder = StateGraph(State)

builder.add_node("guardrail_entrada", guardrail_entrada)
builder.add_node("atendimento", atendimento)
builder.add_node("agente_urgencia", agente_urgencia)
builder.add_node("agente_cardiologista", agente_cardiologista)
builder.add_node("agente_neurologista", agente_neurologista)
builder.add_node("agente_clinicogeral", agente_clinicogeral)
builder.add_node("aprovacao_humana", aprovacao_humana)

builder.add_edge(START, "guardrail_entrada")
builder.add_conditional_edges(
    "guardrail_entrada",
    rotear_guardrail,
    {"liberado": "atendimento", "bloqueado": END},
)
builder.add_conditional_edges(
    "atendimento",
    rotear_triagem,
    {
        "cardiologico": "agente_cardiologista",
        "neurologico": "agente_neurologista",
        "urgente": "agente_urgencia",
        "nao_urgente": "agente_clinicogeral",
    },
)
builder.add_edge("agente_urgencia", "aprovacao_humana")
builder.add_edge("agente_cardiologista", "aprovacao_humana")
builder.add_edge("agente_neurologista", "aprovacao_humana")
builder.add_edge("agente_clinicogeral", "aprovacao_humana")
builder.add_edge("aprovacao_humana", END)

grafo = builder.compile()
