"""
agent-gateway — Punto de entrada único para el usuario. Orquesta llamadas
a sales-service y analytics-service a través de un agente con tool-use.
Puerto por defecto: 8000 (el que se expone al exterior).

Modo demo sin llave de API: exporta AGENT_MODE=mock (ver mock_agent.py).
La orquestación HTTP entre servicios sigue siendo real en ese modo —
solo la decisión de qué herramienta llamar se simula con reglas simples
en vez de un LLM.
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="agent-gateway", version="1.0.0")

_agent = None


def get_agent():
    global _agent
    if _agent is None:
        if os.environ.get("AGENT_MODE", "real").lower() == "mock":
            from mock_agent import MockOrchestratorAgent

            _agent = MockOrchestratorAgent()
        else:
            from agent import OrchestratorAgent

            _agent = OrchestratorAgent()
    return _agent


class ChatRequest(BaseModel):
    mensaje: str


@app.get("/health")
def health():
    return {"status": "ok", "service": "agent-gateway", "agent_mode": os.environ.get("AGENT_MODE", "real")}


@app.post("/chat")
def chat(req: ChatRequest):
    return get_agent().run(req.mensaje)
