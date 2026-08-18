"""finanzas_tributario / preparar_sire — lógica de decisión (RFD v2.9 §4).

Genera y valida los registros RVIE/RCE en formato de carga SIRE desde la
contabilidad. **NUNCA presenta** -- entrega el archivo validado y la
guía paso a paso para que el dueño lo suba él mismo en SUNAT Operaciones
en Línea (SOL). `ejecuta: "servidor_control"` en el catálogo, no Server
Action, por una razón de fondo, no de conveniencia:

1. `aprobacion: "dueno"` — igual que el resto de herramientas
   `servidor_control` de este repo: quien autoriza generar/entregar un
   registro tributario formal tiene que ser específicamente el
   dueño/administrador registrado del tenant.
2. El formato de carga SIRE (RVIE/RCE) es una especificación de SUNAT
   con reglas de validación propias (estructura de campos, RUC/serie/
   correlativo, montos cuadrados) — generarlo correctamente requiere
   lógica de formato dedicada que no tiene sentido reconstruir desde
   cero como parte de esta sesión de implementación del catálogo;
   pertenece al Servidor de Control, donde puede mantenerse versionada
   contra los cambios que SUNAT publique.

Igual que el resto de este directorio: la decisión (¿procede generar el
archivo o falta algo?) es una función pura, sin red — testeable sin
mock. La generación real del archivo SIRE y la guía de presentación
viven aparte, pendientes de que exista el Servidor de Control real.
"""
from __future__ import annotations

from dataclasses import dataclass

REGISTROS_VALIDOS = ("RVIE", "RCE", "ambos")


@dataclass(frozen=True)
class SolicitudSire:
    tenant_id: int
    registro: str
    periodo: str  # "AAAA-MM"
    solicitante_es_dueno: bool


@dataclass(frozen=True)
class ResultadoValidacion:
    valido: bool
    motivo: str


def _periodo_valido(periodo: str) -> bool:
    if len(periodo) != 7 or periodo[4] != "-":
        return False
    anio, mes = periodo[:4], periodo[5:7]
    if not (anio.isdigit() and mes.isdigit()):
        return False
    return 1 <= int(mes) <= 12


def validar_solicitud(solicitud: SolicitudSire) -> ResultadoValidacion:
    """Decide si la solicitud procede. No genera ningun archivo -- devuelve
    la decision para que el Servidor de Control (que tiene la logica de
    formato SIRE real) la ejecute o no."""
    if not solicitud.solicitante_es_dueno:
        return ResultadoValidacion(
            False,
            "aprobacion: dueno -- solo el dueno/administrador registrado del "
            "tenant puede autorizar la preparacion de un registro tributario formal",
        )

    if solicitud.registro not in REGISTROS_VALIDOS:
        return ResultadoValidacion(False, f"registro invalido: {solicitud.registro!r}")

    if not _periodo_valido(solicitud.periodo):
        return ResultadoValidacion(False, "periodo debe tener formato AAAA-MM valido")

    return ResultadoValidacion(True, "ok, lista para generar -- el dueno la presenta el mismo en SOL, esta herramienta nunca presenta")
