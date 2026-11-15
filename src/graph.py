"""Montagem do grafo: START -> atendimento -> END."""

from langgraph.graph import END, START, StateGraph

from src.nodes.atendimento import atendimento
from src.state import State

builder = StateGraph(State)

builder.add_node("atendimento", atendimento)

builder.add_edge(START, "atendimento")
builder.add_edge("atendimento", END)

grafo = builder.compile()
