"""Ciclo de renovación de llaves (dead man's switch) — RFD v2.9 §2 / RF-15.

El Servidor de Control renueva la llave `x_booster_licencia` de cada tenant
cada 24h, SOLO si el tenant está al día en pagos. Sin renovación, la guarda
de cada Server Action bloquea la ejecución a las 48h (ventana de gracia).

Invariante protegida: "El Servidor de Control jamás renueva la llave de un
tenant moroso" — ver tests/test_renovacion.py.
"""
from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

VENTANA_GRACIA_HORAS = 48


@dataclass(frozen=True)
class Tenant:
    id: int
    nombre: str
    al_dia: bool               # estado de pago según Casa Efficax
    url: str = ""              # instancia Odoo (XML-RPC)


@dataclass(frozen=True)
class ResultadoRenovacion:
    tenant_id: int
    renovada: bool
    motivo: str
    token: str | None = None
    fecha: datetime | None = None


def decidir_renovacion(tenant: Tenant, ahora: datetime | None = None) -> ResultadoRenovacion:
    """Decisión pura de renovación (sin efectos). La escritura real vía XML-RPC
    vive aparte para que esta regla sea testeable sin red."""
    ahora = ahora or datetime.now(timezone.utc)
    if not tenant.al_dia:
        return ResultadoRenovacion(
            tenant_id=tenant.id, renovada=False,
            motivo="tenant moroso — la llave NO se renueva (invariante)",
        )
    return ResultadoRenovacion(
        tenant_id=tenant.id, renovada=True, motivo="pago al día",
        token=secrets.token_urlsafe(32), fecha=ahora,
    )


def llave_vigente(fecha_renovacion: datetime, ahora: datetime | None = None) -> bool:
    """Réplica exacta de la guarda instalada en cada Server Action del tenant."""
    ahora = ahora or datetime.now(timezone.utc)
    return (ahora - fecha_renovacion) <= timedelta(hours=VENTANA_GRACIA_HORAS)
