"""
tools.py — Las herramientas del agente NO calculan nada localmente: cada
una hace una petición HTTP a un microservicio distinto. El agente es el
orquestador que decide a cuál servicio pedirle qué, y en qué orden.
"""

from __future__ import annotations

import os

import httpx

SALES_SERVICE_URL = os.environ.get("SALES_SERVICE_URL", "http://localhost:8001")
ANALYTICS_SERVICE_URL = os.environ.get("ANALYTICS_SERVICE_URL", "http://localhost:8002")


def listar_productos() -> list[dict]:
    """Trae el catálogo completo desde sales-service."""
    with httpx.Client(timeout=5.0) as client:
        resp = client.get(f"{SALES_SERVICE_URL}/products")
    resp.raise_for_status()
    return resp.json()


def calcular_rentabilidad(producto_id: str) -> dict:
    """Pide a analytics-service el cálculo de rentabilidad de un producto."""
    with httpx.Client(timeout=5.0) as client:
        resp = client.get(f"{ANALYTICS_SERVICE_URL}/rentabilidad/{producto_id}")
    if resp.status_code == 404:
        return {"error": "Producto no encontrado"}
    resp.raise_for_status()
    return resp.json()


def resumen_ventas(producto_id: str | None = None) -> dict:
    """Pide a analytics-service el resumen de ventas (que a su vez se lo pide a sales-service)."""
    params = {"product_id": producto_id} if producto_id else {}
    with httpx.Client(timeout=5.0) as client:
        resp = client.get(f"{ANALYTICS_SERVICE_URL}/resumen-ventas", params=params)
    resp.raise_for_status()
    return resp.json()


TOOL_DEFINITIONS = [
    {
        "name": "listar_productos",
        "description": "Lista todos los productos del catálogo, con sus datos base.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "calcular_rentabilidad",
        "description": "Calcula el margen real de un producto específico, dado su id.",
        "input_schema": {
            "type": "object",
            "properties": {"producto_id": {"type": "string"}},
            "required": ["producto_id"],
        },
    },
    {
        "name": "resumen_ventas",
        "description": "Resume unidades y dinero facturado, opcionalmente de un solo producto.",
        "input_schema": {
            "type": "object",
            "properties": {"producto_id": {"type": "string"}},
            "required": [],
        },
    },
]

TOOL_IMPLEMENTATIONS = {
    "listar_productos": listar_productos,
    "calcular_rentabilidad": calcular_rentabilidad,
    "resumen_ventas": resumen_ventas,
}
