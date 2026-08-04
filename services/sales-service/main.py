"""
sales-service — Microservicio de datos. Dueño exclusivo de la información
de productos y ventas. Ningún otro servicio accede a estos datos
directamente; todos pasan por su API HTTP. Puerto por defecto: 8001.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException

app = FastAPI(title="sales-service", version="1.0.0")

DATA_DIR = Path(__file__).resolve().parent / "data"


def _load(filename: str) -> list[dict]:
    with open(DATA_DIR / filename, encoding="utf-8") as f:
        return json.load(f)


@app.get("/health")
def health():
    return {"status": "ok", "service": "sales-service"}


@app.get("/products")
def list_products():
    return _load("products.json")


@app.get("/products/{product_id}")
def get_product(product_id: str):
    products = _load("products.json")
    product = next((p for p in products if p["id"] == product_id), None)
    if product is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return product


@app.get("/sales")
def list_sales(product_id: str | None = None):
    sales = _load("sales.json")
    if product_id:
        sales = [s for s in sales if s["producto_id"] == product_id]
    return sales
