"""rrhh / publicar_linkedin — lógica de decisión (RFD v2.9 §4).

Publica la vacante aprobada en el LinkedIn de la empresa. `ejecuta:
"servidor_control"` en el catálogo, no Server Action, por dos razones que
no dependen de qué tan simple sea la lógica:

1. `aprobacion: "dueno"` — igual que `mentor/acceso.py`: quien autoriza
   tiene que ser específicamente el dueño/administrador registrado del
   tenant, no cualquier usuario interno con acceso al chat de Odoo.
2. Publicar en LinkedIn requiere credenciales OAuth de la página de
   empresa del CLIENTE -- eso no existe dentro del sandbox de Odoo del
   tenant (no hay integración de red saliente ahí más allá de lo que Odoo
   ya expone), tiene que vivir en el Servidor de Control, que es quien
   tendría esas credenciales por tenant.

Igual que `mentor/acceso.py` y `mentor/escalamiento.py`: la decisión es
una función pura, sin red — testeable sin mock. La publicación real (API
de LinkedIn) vive aparte, pendiente de que exista el registro de tenants
con sus credenciales propias (ver `app/tenants/`, todavía no construido).
"""
from __future__ import annotations

from dataclasses import dataclass

LIMITE_CARACTERES_LINKEDIN = 3000


@dataclass(frozen=True)
class SolicitudPublicacion:
    tenant_id: int
    puesto_id: int
    texto_publicacion: str
    solicitante_es_dueno: bool
    linkedin_conectado: bool = False


@dataclass(frozen=True)
class ResultadoValidacion:
    valido: bool
    motivo: str


def validar_solicitud(solicitud: SolicitudPublicacion) -> ResultadoValidacion:
    """Decide si la solicitud procede. No publica nada -- devuelve la
    decisión para que el Servidor de Control (que sí tiene las
    credenciales de LinkedIn de ese tenant) ejecute o no."""
    if not solicitud.solicitante_es_dueno:
        return ResultadoValidacion(
            False,
            "aprobacion: dueno -- solo el dueno/administrador registrado del "
            "tenant puede autorizar una publicacion publica en LinkedIn",
        )

    if not solicitud.puesto_id:
        return ResultadoValidacion(False, "falta puesto_id")

    texto = solicitud.texto_publicacion.strip()
    if not texto:
        return ResultadoValidacion(False, "falta texto_publicacion (version aprobada del post)")

    if len(texto) > LIMITE_CARACTERES_LINKEDIN:
        return ResultadoValidacion(
            False,
            f"texto_publicacion tiene {len(texto)} caracteres, LinkedIn "
            f"acepta hasta {LIMITE_CARACTERES_LINKEDIN}",
        )

    if not solicitud.linkedin_conectado:
        return ResultadoValidacion(
            False,
            f"el tenant {solicitud.tenant_id} no tiene la cuenta de LinkedIn de la "
            "empresa conectada todavia -- eso se resuelve en Fase 3 de Booster "
            "(checklist de accesos), no aca",
        )

    return ResultadoValidacion(True, "ok, lista para publicar")
