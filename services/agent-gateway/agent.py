"""
agent.py — Agente orquestador. Igual patrón de bucle de tool-use que en el
otro repo, pero aquí cada tool es una llamada de RED a otro microservicio,
no una función local. El agente actúa como capa de orquestación entre el
usuario (lenguaje natural) y los servicios internos (contratos HTTP/JSON).
"""

from __future__ import annotations

import os

import anthropic

from tools import TOOL_DEFINITIONS, TOOL_IMPLEMENTATIONS

MODEL = "claude-sonnet-4-5"
MAX_TURNS = 6

SYSTEM_PROMPT = """\
Eres el asistente de un panel de ventas. Respondes en español, corto y
concreto. SIEMPRE usa las herramientas para obtener datos reales de los
microservicios — nunca inventes cifras de productos ni de ventas."""


class OrchestratorAgent:
    def __init__(self, api_key: str | None = None):
        self.client = anthropic.Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))

    def run(self, user_message: str) -> dict:
        messages = [{"role": "user", "content": user_message}]
        trace = []

        for _ in range(MAX_TURNS):
            response = self.client.messages.create(
                model=MODEL,
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                tools=TOOL_DEFINITIONS,
                messages=messages,
            )

            if response.stop_reason != "tool_use":
                final_text = "".join(b.text for b in response.content if b.type == "text")
                return {"respuesta": final_text, "herramientas_usadas": trace}

            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                trace.append({"tool": block.name, "input": block.input, "servicio": _tool_to_service(block.name)})
                impl = TOOL_IMPLEMENTATIONS.get(block.name)
                result = impl(**block.input) if impl else {"error": "tool desconocida"}
                tool_results.append(
                    {"type": "tool_result", "tool_use_id": block.id, "content": str(result)}
                )

            messages.append({"role": "user", "content": tool_results})

        return {"respuesta": "Límite de turnos alcanzado.", "herramientas_usadas": trace}


def _tool_to_service(tool_name: str) -> str:
    return {
        "listar_productos": "sales-service (directo)",
        "calcular_rentabilidad": "analytics-service -> sales-service",
        "resumen_ventas": "analytics-service -> sales-service",
    }.get(tool_name, "desconocido")
