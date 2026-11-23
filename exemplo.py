"""Roda o grafo com um prontuario de exemplo, mostra o parecer e pede a aprovacao.

Uso (na pasta do projeto):

    Mac:     .venv/bin/python exemplo.py
    Windows: .venv\\Scripts\\python exemplo.py

Para testar outro prontuario, passe o texto entre aspas:

    .venv/bin/python exemplo.py "Mulher, 34 anos. Renovacao de receita. Sem queixas."

O fluxo pausa no no aprovacao_humana e pergunta no terminal se o parecer foi aprovado.
"""

import sys
import uuid

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.types import Command

from src.graph import builder

PRONTUARIO_PADRAO = (
    "Homem, 58 anos. Dor toracica em aperto ha 40 min, irradiando para o braco "
    "esquerdo, sudorese, PA 90x60 mmHg, SpO2 91%."
)

# Modelos do state que o checkpointer pode reconstruir ao retomar. Sem essa lista, o
# LangGraph avisa que esta lendo tipos nao registrados (e futuramente vai bloquear).
TIPOS_DO_STATE = [
    ("src.state", nome)
    for nome in (
        "ResultadoGuardrail", "AchadoGuardrail", "CidSugerido", "ParecerCardiologico",
        "ParecerNeurologico", "ParecerClinico", "RevisaoHumana",
    )
]

# A pausa (interrupt) precisa de um checkpointer para guardar o estado ate a resposta.
# Aqui, em memoria: o estado some quando o script termina.
checkpointer = InMemorySaver(serde=JsonPlusSerializer(allowed_msgpack_modules=TIPOS_DO_STATE))
grafo = builder.compile(checkpointer=checkpointer)


def mostrar_parecer(revisao: dict) -> None:
    print(f"Urgencia:      {revisao.get('urgencia')}")
    print(f"Especialidade: {revisao.get('especialidade')}")
    print(f"Justificativa: {revisao.get('justificativa')}\n")

    for cid in revisao.get("cids_sugeridos") or []:
        print(f"  {cid['codigo']} - {cid['descricao']}  ({cid['sintoma']})")

    for campo in ("parecer_cardiologico", "parecer_neurologico", "parecer_clinico"):
        parecer = revisao.get(campo)
        if parecer:
            print(f"\n{campo}:")
            for nome, valor in parecer.items():
                print(f"  {nome}: {valor}")
    print()


def perguntar_decisao() -> dict:
    """Pergunta no terminal ate vir uma resposta valida."""
    while True:
        resposta = input("Aprovar o parecer? (s/n): ").strip().lower()
        if resposta in ("s", "sim"):
            return {"aprovado": True}
        if resposta in ("n", "nao", "não"):
            motivo = ""
            while not motivo:
                motivo = input("Motivo da rejeicao: ").strip()
            return {"aprovado": False, "motivo": motivo}
        print("Responda s ou n.")


def main() -> None:
    prontuario = " ".join(sys.argv[1:]) or PRONTUARIO_PADRAO
    # Cada execucao e uma "thread": e por ela que o checkpointer acha o estado pausado.
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    print("Rodando o grafo (a primeira execucao gera o indice do CID-10 e pode levar alguns minutos)...\n")

    resultado = grafo.invoke(
        {"paciente_id": "PAC-001", "prontuario": prontuario, "data_atualizacao": "2026-11-15"},
        config,
    )

    # Enquanto houver pausa, mostra o pacote e retoma com a decisao.
    while "__interrupt__" in resultado:
        pausa = resultado["__interrupt__"][0].value
        if "erro" in pausa:
            print(pausa["erro"])
        mostrar_parecer(pausa)
        resultado = grafo.invoke(Command(resume=perguntar_decisao()), config)

    guardrail = resultado.get("guardrail")
    if guardrail and guardrail.bloqueado:
        print(f"Bloqueado pelo guardrail: {guardrail.motivo}")
        return

    revisao = resultado.get("revisao")
    if revisao and revisao.aprovado:
        print("Parecer aprovado.")
    elif revisao:
        print(f"Parecer rejeitado: {revisao.motivo}")


if __name__ == "__main__":
    main()
