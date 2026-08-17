"""mentor / abrir_ticket_efficax — lógica de decisión.

Escala un problema no resoluble localmente al Helpdesk de "Casa Efficax"
(la instancia Odoo propia de Efficax, no el tenant del cliente). Corre en
el Servidor de Control porque el destino del ticket está en OTRA base de
datos — el tenant del cliente no tiene ni debería tener credenciales
hacia Casa Efficax.

Mismo patrón que `acceso.py`/`llaves/renovacion.py`: acá solo se valida y
se arma el payload (función pura, sin red). El envío real por XML-RPC
hacia Casa Efficax vive aparte.
"""
from __future__ import annotations

from dataclasses import dataclass

SEVERIDADES_VALIDAS = ("baja", "media", "alta")

# Mismo mapeo de severidad -> prioridad de helpdesk.ticket que
# server_actions/implementaciones/ventas_atencion/crear_ticket.py, para que
# un ticket "alta" signifique lo mismo en Casa Efficax que en el tenant del
# cliente.
MAPA_PRIORIDAD = {"baja": "0", "media": "1", "alta": "2"}


@dataclass(frozen=True)
class SolicitudEscalamiento:
    tenant_id: int
    tenant_nombre: str
    asunto: str
    descripcion: str
    severidad: str


@dataclass(frozen=True)
class ResultadoEscalamiento:
    valido: bool
    motivo: str
    payload_ticket: dict | None = None


def construir_ticket(solicitud: SolicitudEscalamiento) -> ResultadoEscalamiento:
    if not solicitud.asunto.strip():
        return ResultadoEscalamiento(False, "falta el asunto")
    if not solicitud.descripcion.strip():
        return ResultadoEscalamiento(False, "falta la descripcion")
    if solicitud.severidad not in SEVERIDADES_VALIDAS:
        return ResultadoEscalamiento(False, f"severidad invalida: {solicitud.severidad!r}")

    payload = {
        "name": f"[{solicitud.tenant_nombre}] {solicitud.asunto.strip()}",
        "description": (
            f"Tenant: {solicitud.tenant_nombre} (id {solicitud.tenant_id})\n\n"
            f"{solicitud.descripcion.strip()}"
        ),
        "priority": MAPA_PRIORIDAD[solicitud.severidad],
    }
    return ResultadoEscalamiento(True, "ok", payload_ticket=payload)
