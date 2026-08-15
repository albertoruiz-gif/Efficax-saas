"""Servidor de Control — API (esqueleto).

Endpoints iniciales: health + estado de tenant (solo lectura).
El ciclo de renovación corre como tarea programada (cron), no como endpoint.
"""
from __future__ import annotations

from fastapi import FastAPI

app = FastAPI(title="Efficax Servidor de Control", version="0.1.0")


@app.get("/health")
def health() -> dict:
    return {"ok": True, "servicio": "servidor-control"}
