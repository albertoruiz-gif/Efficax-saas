"""legal_contratos / generar_contrato_base — lógica de decisión (RFD v2.9 §4).

Genera el borrador de un contrato desde la Biblioteca de Contratos Base
de Efficax (plantillas por país/región validadas por abogado local, 10
tipos). `ejecuta: "servidor_control"` en el catálogo, no Server Action,
por dos razones:

1. `aprobacion: "confirmar"` sobre un documento con implicancia legal
   real -- el criterio de Alberto (18-ago-2026): quien autoriza generar
   un borrador de contrato debería poder auditarse centralizadamente,
   no quedar suelto en el sandbox de cada tenant.
2. **La Biblioteca de Contratos Base es un activo que Efficax mantiene
   una sola vez, centralizado** -- no algo que cada tenant reconstruya.
   Vive en el Servidor de Control para poder actualizarse (nueva
   jurisdicción validada, cláusula corregida por el abogado) sin tocar
   el código de cada cliente.

**Diseño acordado con Alberto (18-ago-2026), no inventado:** las
plantillas NO cambian mucho entre países -- el grueso de las cláusulas
de un contrato de alquiler, locación de servicios, etc. es el mismo.
Lo que sí cambia es la **cláusula de jurisdicción/resolución de
conflictos** (qué instancia previa existe antes de un juzgado, qué ley
aplica) -- eso se parametriza POR PAÍS, no se reescribe la plantilla
entera. El resto de la seguridad viene de dos reglas simples, ambas de
Alberto:
1. **Nunca se sirve una plantilla de una jurisdicción sin validar** --
   si no hay una cláusula de jurisdicción confirmada para ese país, la
   solicitud se rechaza explícito, no se inventa una.
2. **El disclaimer es ineliminable**: "Esta es una PLANTILLA, no tiene
   validez legal por sí sola -- es una ayuda. Debe ser revisada y
   visada por el abogado de la firma antes de firmarse o enviarse."

**Estado real (18-ago-2026):** la Biblioteca de plantillas por tipo de
contrato (el texto real de cada uno de los 10 tipos) todavía NO está
cargada -- Alberto va a proveer contratos de Perú reales, ya validados
por un abogado, como base. Hasta que existan, esta función solo puede
VALIDAR la solicitud y resolver la cláusula de jurisdicción -- nunca
redacta el cuerpo de un contrato por su cuenta. `CLAUSULAS_JURISDICCION`
y `BIBLIOTECA_PLANTILLAS` son los dos registros que se completan cuando
llegue ese contenido real.
"""
from __future__ import annotations

from dataclasses import dataclass, field

TIPOS_VALIDOS = (
    "alquiler", "locacion_servicios", "laboral_tiempo_completo", "compra_venta",
    "servicios_limpieza", "transporte_personal", "suministro", "delivery_mercancias",
    "societario", "mantenimiento_industrial",
)

DISCLAIMER = (
    "Esta es una PLANTILLA, no tiene validez legal por si sola -- es una "
    "ayuda. Debe ser revisada y visada por el abogado de la firma antes "
    "de firmarse o enviarse."
)

# Cláusula de jurisdicción/resolución de conflictos por país -- la única
# parte que varía entre plantillas según el diseño acordado. Vacío salvo
# Perú (el único caso que Alberto ya describió: centros de conciliación
# antes de instancia judicial). Se completa país por país conforme se
# valide con asesoría legal local -- nunca se inventa una entrada nueva.
CLAUSULAS_JURISDICCION: dict[str, str] = {
    "Peru": (
        "En caso de incumplimiento, las partes se someten a las leyes de "
        "la Republica del Peru. Previo a cualquier accion judicial, las "
        "partes agotaran la via conciliatoria ante un centro de "
        "conciliacion extrajudicial autorizado, conforme a la Ley de "
        "Conciliacion vigente. De no llegarse a un acuerdo, la "
        "controversia se resolvera ante los juzgados civiles competentes "
        "del domicilio de la parte demandada."
    ),
}

# Biblioteca real de plantillas por (tipo, pais) -- VACÍA hasta que
# Alberto entregue los contratos de Peru ya validados. No se fabrica
# contenido de relleno: mientras una clave no esté acá, la solicitud de
# ese (tipo, pais) se rechaza explícito en validar_solicitud().
BIBLIOTECA_PLANTILLAS: dict[tuple[str, str], str] = {}


@dataclass(frozen=True)
class ParteContrato:
    nombre: str
    rol: str
    documento: str = ""


@dataclass(frozen=True)
class SolicitudContrato:
    tenant_id: int
    tipo: str
    pais: str
    region: str
    partes: tuple[ParteContrato, ...] = field(default_factory=tuple)
    datos: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ResultadoValidacion:
    valido: bool
    motivo: str
    clausula_jurisdiccion: str | None = None
    disclaimer: str = DISCLAIMER


def validar_solicitud(solicitud: SolicitudContrato) -> ResultadoValidacion:
    """Decide si la solicitud procede y con qué cláusula de jurisdicción.
    NO redacta el cuerpo del contrato -- eso viene de
    BIBLIOTECA_PLANTILLAS, que hoy está vacía a propósito."""
    if solicitud.tipo not in TIPOS_VALIDOS:
        return ResultadoValidacion(False, f"tipo invalido: {solicitud.tipo!r}")

    if not solicitud.pais.strip():
        return ResultadoValidacion(False, "falta pais")

    if not solicitud.region.strip():
        return ResultadoValidacion(False, "falta region")

    if len(solicitud.partes) < 2:
        return ResultadoValidacion(False, "se necesitan al menos 2 partes")

    for p in solicitud.partes:
        if not p.nombre.strip() or not p.rol.strip():
            return ResultadoValidacion(False, "cada parte necesita nombre y rol")

    clausula = CLAUSULAS_JURISDICCION.get(solicitud.pais)
    if clausula is None:
        return ResultadoValidacion(
            False,
            f"no hay una clausula de jurisdiccion validada para {solicitud.pais!r} todavia -- "
            "nunca se sirve una plantilla de una jurisdiccion sin validar",
        )

    if (solicitud.tipo, solicitud.pais) not in BIBLIOTECA_PLANTILLAS:
        return ResultadoValidacion(
            False,
            f"la plantilla real de '{solicitud.tipo}' para {solicitud.pais!r} todavia no esta "
            "cargada en la Biblioteca de Contratos Base -- pendiente de que Alberto la provea",
            clausula_jurisdiccion=clausula,
        )

    return ResultadoValidacion(True, "ok, lista para generar", clausula_jurisdiccion=clausula)
