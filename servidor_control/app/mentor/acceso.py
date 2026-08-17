"""mentor / actualizar_perfil_acceso — lógica de decisión (RFD v2.9 §4,
Fase 3 de 01-booster-implementador.md).

Cambia el perfil de acceso de un empleado (alta, cambio de perfil, baja)
sin reabrir el wizard de provisioning de Booster. Corre en el Servidor de
Control (no como Server Action en el tenant del cliente) porque
`aprobacion: "dueno"` es un nivel más estricto que "confirmar": exige que
quien autoriza sea específicamente el dueño/administrador registrado del
tenant, no cualquier usuario interno — esa verificación de identidad no
debería quedar a criterio del código que corre dentro del propio tenant
del cliente.

Igual que `llaves/renovacion.py`: la decisión es una función pura, sin
red — testeable sin mock. La escritura real (XML-RPC hacia `res.users`/
`res.groups` del tenant) vive aparte (pendiente: no hay todavía un
registro de tenants con credenciales propias — ver `app/tenants/`).

El mapeo perfil → grupos de Odoo (`gerente_general`, `gerente_comercial`,
`administrativo`, `operacion`, ...) lo define Booster en su Fase 3 —
varía por tenant, así que NUNCA se hardcodea acá: llega como parámetro
(`mapeo_perfil_grupos`), y si el perfil pedido no está en ese mapeo, la
solicitud se rechaza explícito en vez de inventar un grupo.
"""
from __future__ import annotations

from dataclasses import dataclass

ACCIONES_VALIDAS = ("alta", "cambio_perfil", "baja")


@dataclass(frozen=True)
class SolicitudCambioAcceso:
    tenant_id: int
    usuario: str
    accion: str  # alta | cambio_perfil | baja
    solicitante_es_dueno: bool
    perfil_nuevo: str | None = None
    motivo: str = ""


@dataclass(frozen=True)
class ResultadoValidacion:
    valido: bool
    motivo: str
    grupos_a_asignar: tuple[str, ...] | None = None


def validar_solicitud(
    solicitud: SolicitudCambioAcceso,
    mapeo_perfil_grupos: dict[str, tuple[str, ...]],
) -> ResultadoValidacion:
    """Decide si la solicitud procede y, si es alta/cambio_perfil, con qué
    grupos de Odoo. No escribe nada — devuelve la decisión."""
    if not solicitud.solicitante_es_dueno:
        return ResultadoValidacion(
            False,
            "aprobacion: dueno -- solo el dueno/administrador registrado del "
            "tenant puede autorizar cambios de acceso, no otro usuario interno",
        )

    if solicitud.accion not in ACCIONES_VALIDAS:
        return ResultadoValidacion(False, f"accion invalida: {solicitud.accion!r}")

    if not solicitud.usuario.strip():
        return ResultadoValidacion(False, "falta el usuario (login o nombre)")

    if solicitud.accion == "baja":
        return ResultadoValidacion(
            True, "baja: se retiran todos los grupos de negocio, se conserva el login",
            grupos_a_asignar=(),
        )

    # alta / cambio_perfil: perfil_nuevo es obligatorio y debe existir en el
    # mapeo de Fase 3 de ESTE tenant -- nunca se asume un grupo por defecto.
    if not solicitud.perfil_nuevo:
        return ResultadoValidacion(False, "perfil_nuevo es obligatorio para alta/cambio_perfil")

    grupos = mapeo_perfil_grupos.get(solicitud.perfil_nuevo)
    if grupos is None:
        return ResultadoValidacion(
            False,
            f"el perfil '{solicitud.perfil_nuevo}' no esta definido en el mapeo de "
            "Fase 3 de este tenant -- hay que crearlo en Booster antes de asignarlo",
        )

    return ResultadoValidacion(True, "ok", grupos_a_asignar=tuple(grupos))
