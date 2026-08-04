"""
analytics-service — Microservicio de negocio. No tiene datos propios: para
calcular rentabilidad, le PIDE el producto al sales-service por HTTP. Esto
es integración real de microservicios (no imports de Python entre ellos):
cada servicio es un proceso independiente, con su propio contrato HTTP, que
se podría desplegar y escalar por separado. Puerto por defecto: 8002.
"""

from __future__ import annotations

import os

import httpx
from fastapi import FastAPI, HTTPException

app = FastAPI(title="analytics-service", version="1.0.0")

SALES_SERVICE_URL = os.environ.get("SALES_SERVICE_URL", "http://localhost:8001")


@app.get("/health")
def health():
    return {"status": "ok", "service": "analytics-service"}


@app.get("/rentabilidad/{product_id}")
def rentabilidad(product_id: str):
    with httpx.Client(timeout=5.0) as client:
        resp = client.get(f"{SALES_SERVICE_URL}/products/{product_id}")
    if resp.status_code == 404:
        raise HTTPException(status_code=404, detail="Producto no encontrado en sales-service")
    resp.raise_for_status()
    p = resp.json()

    n = 100
    entregados = n * (p["tasa_entrega"] / 100)
    no_entregados = n - entregados

    ingresos = entregados * p["precio"]
    costo_producto_total = n * (p["costo_proveedor"] + p["flete_ida"])
    costo_retorno_total = no_entregados * p["flete_retorno"]
    costo_ads_total = n * p["cpa"]

    utilidad_total = ingresos - costo_producto_total - costo_retorno_total - costo_ads_total
    utilidad_por_pedido = utilidad_total / n
    margen_pct = round((utilidad_total / ingresos) * 100, 1) if ingresos > 0 else 0

    if margen_pct >= 15:
        estado = "rentable"
    elif margen_pct >= 5:
        estado = "ajustado"
    else:
        estado = "perdida"

    return {
        "producto_id": product_id,
        "producto": p["nombre"],
        "margen_pct": margen_pct,
        "utilidad_por_pedido": round(utilidad_por_pedido),
        "estado": estado,
    }


@app.get("/resumen-ventas")
def resumen_ventas(product_id: str | None = None):
    params = {"product_id": product_id} if product_id else {}
    with httpx.Client(timeout=5.0) as client:
        resp = client.get(f"{SALES_SERVICE_URL}/sales", params=params)
    resp.raise_for_status()
    ventas = resp.json()

    return {
        "num_ventas": len(ventas),
        "total_unidades": sum(v["unidades"] for v in ventas),
        "total_valor": sum(v["valor"] for v in ventas),
    }
