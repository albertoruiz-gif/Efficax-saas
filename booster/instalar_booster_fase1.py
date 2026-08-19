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
    {"name": "x_fase_actual", "field_description": "Fase actual", "ttype": "selection",
     "selection": "[('descubrimiento','1 Descubrimiento'),('propuesta','2 Propuesta y datos'),('provisioning','3 Provisioning'),('ajustes','4 Ajustes por agente'),('residencia','5 Residencia')]"},
    # Camino del wizard (19-ago-2026): UN wizard que se bifurca, no 3 wizards. Se
    # descubre en Fase 1 con dos preguntas bisagra (tiene Odoo? / ya opera con datos?).
    {"name": "x_camino", "field_description": "Camino de implementacion", "ttype": "selection",
     "selection": "[('A','A - Nuevo, sin operacion previa'),('B','B - Ya opera, sin Odoo (Excel/otro sistema)'),('C','C - Ya tiene Odoo')]"},
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
        "camino": {"type": "string", "enum": ["A", "B", "C"], "description": "Camino de implementacion, UNA VEZ que lo descubras en Fase 1 con las dos preguntas bisagra: A = negocio nuevo sin operacion previa; B = ya opera con datos reales pero SIN Odoo (Excel, otro sistema, papel); C = ya tiene Odoo funcionando. No lo adivines: si aun no lo sabes, no lo pases."},
    },
    "required": ["tenant", "dueno_nombre", "dueno_email", "fase", "respuestas_json"],
}

TOPIC_INSTRUCCIONES = (
    "Estas en la Fase 1 (Descubrimiento) del wizard de implementacion. Objetivo: recolectar, "
    "en conversacion natural y SIN jerga tecnica, estos datos del negocio: pais y moneda, "
    "regimen fiscal (en Peru: RUC, regimen, boleta/factura, OSE/PSE propio o guiado), "
    "industria y que vende, numero de usuarios y roles, si ya tiene dominio/correo propio, "
    "y LAS DOS PREGUNTAS BISAGRA que definen el camino: (1) si ya tiene Odoo funcionando "
    "[si SI -> camino C: avisa que se hace un checklist de deteccion de lo existente antes de "
    "continuar -- usa la herramienta evaluar_implementacion del tema Norma de implementacion, "
    "y nada de lo que ya tiene se toca]; (2) si NO tiene Odoo, pregunta explicitamente si YA "
    "OPERA con datos reales en otro lado (Excel, otro sistema, papel) o es un negocio nuevo "
    "[si ya opera -> camino B: en Fase 2 le vas a entregar plantillas para migrar productos, "
    "clientes, saldos; si es nuevo -> camino A: no hay nada que migrar, arranca limpio]. "
    "Guarda el camino (A, B o C) con guardar_avance en cuanto lo tengas claro. "
    "Y por ultimo sus 3 dolores principales del negocio. "
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


def _sincronizar_campos(o: Odoo, modelo_id: int) -> None:
    """Idempotente POR CAMPO (19-ago-2026): crea los que faltan y migra el
    tipo de los que cambiaron. Antes, si el modelo ya existia, el
    instalador no tocaba campos -- asi que agregar x_camino o pasar
    x_fase_actual de char a selection no llegaba nunca al tenant.

    Migracion char -> selection preservando datos: Odoo no deja cambiar
    ttype de un campo manual con registros. Se hace en 3 pasos: leer los
    valores actuales, eliminar el campo viejo, crear el nuevo con el
    mismo nombre, y reescribir los valores (que ya son claves validas del
    selection porque guardar_avance siempre valido contra FASES_VALIDAS)."""
    existentes = {
        f["name"]: f
        for f in o.execute("ir.model.fields", "search_read", [("model_id", "=", modelo_id)], fields=["name", "ttype"])
    }
    for campo in CAMPOS_IMPLEMENTACION:
        actual = existentes.get(campo["name"])
        if actual is None:
            o.execute("ir.model.fields", "create", {**campo, "model_id": modelo_id, "state": "manual"})
            print("  campo creado:", campo["name"], "(" + campo["ttype"] + ")")
        elif actual["ttype"] != campo["ttype"]:
            valores = {
                r["id"]: r[campo["name"]]
                for r in o.execute("x_booster_implementacion", "search_read", [], fields=[campo["name"]])
            }
            o.execute("ir.model.fields", "unlink", [actual["id"]])
            o.execute("ir.model.fields", "create", {**campo, "model_id": modelo_id, "state": "manual"})
            for rid, v in valores.items():
                if v:
                    o.execute("x_booster_implementacion", "write", [rid], {campo["name"]: v})
            print("  campo migrado:", campo["name"], actual["ttype"], "->", campo["ttype"], "(" + str(len(valores)) + " registros preservados)")


def crear_modelo_implementacion(o: Odoo) -> int:
    existente = o.execute("ir.model", "search", [("model", "=", "x_booster_implementacion")])
    if existente:
        _sincronizar_campos(o, existente[0])
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


ICONO_PATH = Path(__file__).resolve().parent / "assets" / "icono_booster_b.png"


def crear_menu_app(o: Odoo) -> int:
    import base64

    existente = o.execute("ir.ui.menu", "search", [("name", "=", "Booster"), ("parent_id", "=", False)])
    if existente:
        menu_id = existente[0]
    else:
        accion_id = o.execute("ir.actions.act_window", "create", {
            "name": "Booster — Implementaciones",
            "res_model": "x_booster_implementacion",
            "view_mode": "list,form",
        })
        menu_id = o.execute("ir.ui.menu", "create", {
            "name": "Booster",
            "action": "ir.actions.act_window," + str(accion_id),
            "sequence": 1,
        })

    # web_icon_data en un write() separado: si se manda junto con web_icon en
    # la misma llamada, Odoo lo vacía (comportamiento verificado en vivo, no
    # documentado) -- por eso va aparte, siempre al final.
    if ICONO_PATH.exists():
        data_b64 = base64.b64encode(ICONO_PATH.read_bytes()).decode("ascii")
        o.execute("ir.ui.menu", "write", [menu_id], {"web_icon_data": data_b64})

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
    }
    if agente_existente:
        # (4, id) AGREGA el topic sin borrar los demas (ej. el de la Norma de
        # implementacion, instalado por otro script). Antes era (6, 0, [...]),
        # que reemplaza TODOS los topics -- reinstalar Fase 1 habria borrado
        # la Norma. Tampoco se pisa el system_prompt: el aviso de IA y la regla
        # de no enumerar agentes se agregaron en vivo el 18-ago-2026 y viven
        # solo en el tenant; reescribirlo aqui los borraria.
        valores_agente.pop("system_prompt", None)
        valores_agente["topic_ids"] = [(4, topic_id)]
        o.execute("ai.agent", "write", agente_existente, valores_agente)
        return agente_existente[0]
    valores_agente["topic_ids"] = [(6, 0, [topic_id])]
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
