"""Instalador de Booster (carcasa) — Fase 1: Descubrimiento.

Deja Booster instalado en un tenant como app visible: modelo persistente
`x_booster_implementacion`, el ícono/menú "Booster", la Server Action
`guardar_avance_wizard` y el agente conversacional `Booster` con su tema
de Fase 1.

Idempotente: se puede correr varias veces sin duplicar nada (busca por
`model`/`name` antes de crear).

Por qué existe este script en vez de solo los comandos sueltos que se
usaron para instalar por primera vez en Efficax (16-ago-2026): la
instrucción explícita fue que TODO quede documentado y versionado en
GitHub — nada de "lo hice por consola y ya" — así cuando haya que
reinstalar Booster en un tenant de cliente real (cuando exista ese
flujo), el proceso completo está acá, no en el historial de una sesión.

Uso:
    python instalar_booster_fase1.py
(lee credenciales de scripts/credenciales_booster.env, igual que el resto
de scripts de instalación del repo)
"""
from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
sys.path.insert(0, str(RAIZ / "booster"))

from booster_rpc import Odoo  # noqa: E402

CAMPOS_IMPLEMENTACION = [
    {"name": "x_tenant", "field_description": "Tenant", "ttype": "char"},
    {"name": "x_dueno_nombre", "field_description": "Nombre del dueno/admin", "ttype": "char"},
    {"name": "x_dueno_email", "field_description": "Email del dueno/admin", "ttype": "char"},
    {"name": "x_fase_actual", "field_description": "Fase actual (descubrimiento/propuesta/provisioning/ajustes/residencia)", "ttype": "char"},
    {"name": "x_respuestas_json", "field_description": "Respuestas de la entrevista (JSON)", "ttype": "text"},
    {"name": "x_checkpoints", "field_description": "Checkpoints con fecha", "ttype": "text"},
    {"name": "x_pendientes", "field_description": "Pendientes", "ttype": "text"},
    {"name": "x_fecha_inicio", "field_description": "Fecha de inicio", "ttype": "datetime"},
    {"name": "x_fecha_ultimo_avance", "field_description": "Fecha del ultimo avance", "ttype": "datetime"},
]

ESQUEMA_GUARDAR_AVANCE = {
    "type": "object",
    "properties": {
        "tenant": {"type": "string", "description": "Nombre del negocio/tenant que se esta implementando"},
        "dueno_nombre": {"type": "string", "description": "Nombre del dueno o administrador designado (unico con quien conversa Booster)"},
        "dueno_email": {"type": "string", "description": "Email del dueno o administrador designado"},
        "fase": {"type": "string", "enum": ["descubrimiento", "propuesta", "provisioning", "ajustes", "residencia"], "description": "Fase actual del wizard"},
        "respuestas_json": {"type": "string", "description": 'Texto JSON con las respuestas nuevas de la entrevista, ej: {"pais":"Peru","moneda":"PEN"}. Se combina con lo ya guardado, no lo reemplaza.'},
        "checkpoint_nota": {"type": "string", "description": "Nota corta opcional para el registro de checkpoints"},
        "pendiente": {"type": "string", "description": "Algo pendiente opcional para agregar a la lista de pendientes"},
    },
    "required": ["tenant", "dueno_nombre", "dueno_email", "fase", "respuestas_json"],
}

TOPIC_INSTRUCCIONES = (
    "Estas en la Fase 1 (Descubrimiento) del wizard de implementacion. Objetivo: recolectar, "
    "en conversacion natural y SIN jerga tecnica, estos datos del negocio: pais y moneda, "
    "regimen fiscal (en Peru: RUC, regimen, boleta/factura, OSE/PSE propio o guiado), "
    "industria y que vende, numero de usuarios y roles, si ya tiene dominio/correo propio, "
    "si ya tiene Odoo (y en ese caso avisa que se necesita hacer el checklist de deteccion antes "
    "de continuar, no lo intentes tu mismo todavia), y sus 3 dolores principales del negocio. "
    "Guarda el avance con la herramienta de guardar avance despues de CADA respuesta relevante "
    "-- nunca esperes a tener todo para guardar, la conversacion se puede cortar. "
    'Al guardar, siempre pasa fase="descubrimiento". Solo conversas con el dueno o administrador '
    "designado; si otra persona te escribe, redirigela con amabilidad. Cuando completes las 6 "
    "preguntas de Fase 1, resume lo recolectado y avisa que la Fase 2 (Propuesta y datos) esta "
    "en construccion todavia -- no prometas continuar automaticamente."
)

SYSTEM_PROMPT = (
    "Eres Booster, el implementador de Efficax. Tu trabajo es dejar el Odoo del negocio que te "
    "esta usando operando con sus agentes configurados, sin consultores. Hablas claro y sin jerga "
    "tecnica -- tu usuario es un dueno de negocio, no un ingeniero -- pero tu criterio es de "
    "gerente de alto nivel (perfil tipo MBA): entiendes margen, flujo de caja, riesgo y "
    "priorizacion, y recomiendas con ese estandar, no como un instalador de software. Solo "
    "conversas con el dueno/administrador designado (y con quien el autorice explicitamente); a "
    "cualquier otra persona la rediriges con amabilidad. Trabajas por fases y NUNCA saltas una "
    "fase sin cerrar la anterior. Todo lo que configuras queda registrado; todo es reversible. "
    "Ahora mismo solo tienes construida la Fase 1 (Descubrimiento) -- las fases 2 a 5 estan en "
    "construccion, no prometas que las vas a ejecutar todavia."
)


def crear_modelo_implementacion(o: Odoo) -> int:
    existente = o.execute("ir.model", "search", [("model", "=", "x_booster_implementacion")])
    if existente:
        return existente[0]

    modelo_id = o.execute("ir.model", "create", {
        "name": "Booster Implementacion",
        "model": "x_booster_implementacion",
        "state": "manual",
    })
    for campo in CAMPOS_IMPLEMENTACION:
        o.execute("ir.model.fields", "create", {**campo, "model_id": modelo_id, "state": "manual"})
    o.execute("ir.model.access", "create", {
        "name": "x_booster_implementacion acceso base",
        "model_id": modelo_id,
        "perm_read": True,
        "perm_write": True,
        "perm_create": True,
        "perm_unlink": False,
    })
    return modelo_id


def crear_menu_app(o: Odoo) -> int:
    existente = o.execute("ir.ui.menu", "search", [("name", "=", "Booster"), ("parent_id", "=", False)])
    if existente:
        return existente[0]

    accion_id = o.execute("ir.actions.act_window", "create", {
        "name": "Booster — Implementaciones",
        "res_model": "x_booster_implementacion",
        "view_mode": "list,form",
    })
    menu_id = o.execute("ir.ui.menu", "create", {
        "name": "Booster",
        "action": "ir.actions.act_window," + str(accion_id),
        "sequence": 1,
        "web_icon": "fa-rocket,#7C3AED,#FFFFFF",
    })
    return menu_id


def instalar_tool_guardar_avance(o: Odoo, modelo_implementacion_id: int) -> int:
    import json

    sys.path.insert(0, str(RAIZ / "server_actions"))
    sys.path.insert(0, str(RAIZ / "booster"))
    from implementaciones.guardar_avance_wizard import CODIGO  # noqa: PLC0415

    existentes = o.execute("ir.actions.server", "search", [("name", "=", "booster: guardar_avance_wizard")])
    valores = {
        "name": "booster: guardar_avance_wizard",
        "model_id": modelo_implementacion_id,
        "state": "code",
        "code": CODIGO,
        "use_in_ai": True,
        "ai_tool_description": (
            "Guarda el avance del wizard de implementacion de Booster (respuestas de la entrevista, "
            "fase actual, checkpoints, pendientes). Usar SIEMPRE despues de cada respuesta relevante "
            "del dueno, para no perder nada si la conversacion se corta."
        ),
        "ai_tool_schema": json.dumps(ESQUEMA_GUARDAR_AVANCE, ensure_ascii=False),
    }
    if existentes:
        o.execute("ir.actions.server", "write", existentes, valores)
        return existentes[0]
    return o.execute("ir.actions.server", "create", valores)


def crear_agente_booster(o: Odoo, tool_id: int) -> int:
    topic_existente = o.execute("ai.topic", "search", [("name", "=", "Booster — Fase 1: Descubrimiento")])
    valores_topic = {
        "name": "Booster — Fase 1: Descubrimiento",
        "instructions": TOPIC_INSTRUCCIONES,
        "tool_ids": [(6, 0, [tool_id])],
    }
    if topic_existente:
        o.execute("ai.topic", "write", topic_existente, valores_topic)
        topic_id = topic_existente[0]
    else:
        topic_id = o.execute("ai.topic", "create", valores_topic)

    agente_existente = o.execute("ai.agent", "search", [("name", "=", "Booster")])
    valores_agente = {
        "name": "Booster",
        "system_prompt": SYSTEM_PROMPT,
        "llm_model": "gpt-5",
        "response_style": "balanced",
        "restrict_to_sources": True,
        "topic_ids": [(6, 0, [topic_id])],
    }
    if agente_existente:
        o.execute("ai.agent", "write", agente_existente, valores_agente)
        return agente_existente[0]
    return o.execute("ai.agent", "create", valores_agente)


def instalar(o: Odoo) -> dict:
    modelo_id = crear_modelo_implementacion(o)
    menu_id = crear_menu_app(o)
    tool_id = instalar_tool_guardar_avance(o, modelo_id)
    agente_id = crear_agente_booster(o, tool_id)
    return {"modelo_id": modelo_id, "menu_id": menu_id, "tool_id": tool_id, "agente_id": agente_id}


if __name__ == "__main__":
    resultado = instalar(Odoo())
    print("Booster (Fase 1) instalado:", resultado)
