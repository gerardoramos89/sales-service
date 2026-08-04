"""
mock_agent.py — Misma idea que en sales-rag-agent: un agente que simula
las decisiones de un LLM con reglas simples, para poder probar todo el
flujo (agent-gateway -> analytics-service -> sales-service, por HTTP real)
sin necesitar ANTHROPIC_API_KEY. Actívalo con AGENT_MODE=mock.

Ojo: esto SIGUE haciendo llamadas HTTP reales a los otros microservicios
— lo único "mock" es la decisión de qué herramienta llamar, no la
comunicación entre servicios (esa es real incluso en modo demo).
"""

from __future__ import annotations

import re

from tools import calcular_rentabilidad, listar_productos, resumen_ventas


class MockOrchestratorAgent:
    def run(self, user_message: str) -> dict:
        msg = user_message.lower()
        trace = []

        if re.search(r"rentab|margen|p[ée]rdida|gan[ao]", msg):
            productos = listar_productos()
            trace.append({"tool": "listar_productos", "input": {}, "servicio": "sales-service (directo)"})
            match = _find_product_by_keyword(productos, msg)
            if not match:
                return {"respuesta": "[modo demo] No identifiqué el producto en tu pregunta.", "herramientas_usadas": trace}
            resultado = calcular_rentabilidad(match["id"])
            trace.append({"tool": "calcular_rentabilidad", "input": {"producto_id": match["id"]}, "servicio": "analytics-service -> sales-service"})
            estado_txt = {"rentable": "es rentable ✅", "ajustado": "está ajustado ⚠️", "perdida": "está en PÉRDIDA ❌"}[resultado["estado"]]
            return {
                "respuesta": f"[modo demo] {resultado['producto']} {estado_txt}. Margen: {resultado['margen_pct']}%.",
                "herramientas_usadas": trace,
            }

        if re.search(r"vend|total|cu[aá]nto|factur", msg):
            productos = listar_productos()
            match = _find_product_by_keyword(productos, msg)
            producto_id = match["id"] if match else None
            resumen = resumen_ventas(producto_id)
            trace.append({"tool": "resumen_ventas", "input": {"producto_id": producto_id}, "servicio": "analytics-service -> sales-service"})
            nombre = match["nombre"] if match else "todos tus productos"
            return {
                "respuesta": f"[modo demo] Ventas de {nombre}: {resumen['num_ventas']} ventas, {resumen['total_unidades']} unidades, ${resumen['total_valor']:,} COP.",
                "herramientas_usadas": trace,
            }

        productos = listar_productos()
        trace.append({"tool": "listar_productos", "input": {}, "servicio": "sales-service (directo)"})
        nombres = ", ".join(p["nombre"] for p in productos[:5])
        return {"respuesta": f"[modo demo] Catálogo: {nombres}.", "herramientas_usadas": trace}


def _find_product_by_keyword(productos: list[dict], msg: str) -> dict | None:
    for p in productos:
        palabras = p["nombre"].lower().split() + p["categoria"].lower().split()
        if any(palabra in msg for palabra in palabras if len(palabra) > 3):
            return p
    return None
