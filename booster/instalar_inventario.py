"""Inventario de Booster -- el registro de TODO lo que Booster crea en un
tenant (spec 01-booster-implementador.md §Inventario), y el kill-switch
capa 2 que se apoya en el.

## Por que existe (y por que es prerrequisito de la Fase 3)

El modelo de cobro de Efficax depende de una invariante: "lo nuestro se
apaga; lo suyo jamas". Si un cliente deja de pagar, se apagan UNICAMENTE
las piezas que Booster agrego -- y el cliente sigue operando exactamente
como antes de conocernos. Eso solo es posible si cada cosa que Booster
crea queda registrada con su etiqueta. Sin inventario, apagar a un
cliente es a ciegas: o no se apaga todo, o se toca algo suyo.

El kill-switch tiene 3 capas (spec §Regla de cancelacion). La capa 1 ya
existe (la llave `x_booster_licencia` + guarda en cada Server Action).
Esta es la capa 2: archivar (`active=False`) lo inventariado como
"creado por Booster". La capa 3 (Servidor de Control deja de responder)
es del Servidor de Control.

## Modelo `x_booster_inventario` -- una fila por registro creado

- x_modelo: modelo Odoo del registro (ej. 'ai.agent', 'ir.actions.server')
- x_res_id: id del registro en ese modelo
- x_nombre: nombre legible, para el reporte al dueno
- x_etiqueta: 'creado_por_booster' | 'preexistente'
- x_receta: receta/fase de origen (ej. 'fase3.provisioning.agentes')
- x_fecha: cuando se registro
- x_estado: 'activo' | 'archivado' -- que hizo el kill-switch con el
- x_archivable: si el modelo soporta active=False (no todos lo tienen:
  ir.model.fields no, por ejemplo) -- lo que no es archivable se
  inventaria igual (para auditoria y rollback) pero el kill-switch lo
  salta y lo reporta.

## Dos herramientas (Server Actions con guarda, como todo lo de Booster)

- `booster: registrar_en_inventario` -- la llama cada receta al crear
  algo. Idempotente por (modelo, res_id): registrar dos veces no duplica.
- `booster: killswitch_inventario` -- accion 'apagar' | 'reactivar' |
  'listar'. 'apagar' archiva TODO lo 'creado_por_booster' que sea
  archivable y NUNCA toca lo 'preexistente'; 'reactivar' lo revierte;
  'listar' devuelve el inventario para el reporte. Requiere confirmacion
  explicita (param confirmar=true) para apagar: es la accion mas
  delicada de todo Booster.

## Etiqueta 'preexistente' -- de donde sale

Del camino C (cliente que ya tiene Odoo): Fase 1-bis inventaria lo que
YA habia, etiquetado 'preexistente -- prohibido tocar'. Hoy
`evaluar_implementacion` detecta vacios pero todavia no escribe en el
inventario; cuando se construya Fase 1-bis completa, cada agente /
automatizacion / Server Action previa que encuentre se registra aca con
esa etiqueta. El kill-switch ya los respeta desde ahora.

Uso:
    python instalar_inventario.py            # crea modelo + 2 tools + topic
"""
from __future__ import annotations

import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
sys.path.insert(0, str(RAIZ / "server_actions"))
sys.path.insert(0, str(RAIZ / "booster"))

from booster_rpc import Odoo  # noqa: E402

CAMPOS_INVENTARIO = [
    {"name": "x_modelo", "field_description": "Modelo Odoo", "ttype": "char", "required": True},
    {"name": "x_res_id", "field_description": "ID del registro", "ttype": "integer", "required": True},
    {"name": "x_nombre", "field_description": "Nombre legible", "ttype": "char"},
    {"name": "x_etiqueta", "field_description": "Etiqueta", "ttype": "selection",
     "selection": "[('creado_por_booster','Creado por Booster'),('preexistente','Preexistente - prohibido tocar')]", "required": True},
    {"name": "x_receta", "field_description": "Receta / fase de origen", "ttype": "char"},
    {"name": "x_fecha", "field_description": "Fecha de registro", "ttype": "datetime"},
    {"name": "x_estado", "field_description": "Estado", "ttype": "selection",
     "selection": "[('activo','Activo'),('archivado','Archivado por kill-switch')]"},
    {"name": "x_archivable", "field_description": "Soporta active=False", "ttype": "boolean"},
]

ESQUEMA_REGISTRAR = {
    "type": "object",
    "properties": {
        "modelo": {"type": "string", "description": "Modelo Odoo del registro creado, ej. 'ai.agent', 'ir.actions.server', 'res.users'"},
        "res_id": {"type": "integer", "description": "ID del registro en ese modelo"},
        "nombre": {"type": "string", "description": "Nombre legible para el reporte al dueno"},
        "etiqueta": {"type": "string", "enum": ["creado_por_booster", "preexistente"], "description": "'creado_por_booster' para lo que Booster agrego; 'preexistente' para lo que el cliente YA tenia (camino C) y esta prohibido tocar"},
        "receta": {"type": "string", "description": "Receta o fase de origen, ej. 'fase3.provisioning.agentes'"},
    },
    "required": ["modelo", "res_id", "etiqueta"],
}

ESQUEMA_KILLSWITCH = {
    "type": "object",
    "properties": {
        "accion": {"type": "string", "enum": ["listar", "apagar", "reactivar"], "description": "'listar' devuelve el inventario; 'apagar' archiva todo lo creado por Booster (nunca lo preexistente); 'reactivar' lo revierte"},
        "confirmar": {"type": "boolean", "description": "Obligatorio en true para 'apagar' o 'reactivar'. Nunca lo pongas en true sin confirmacion explicita del dueno o de Efficax."},
    },
    "required": ["accion"],
}

TOPIC_INSTRUCCIONES = """Eres Booster manejando el INVENTARIO: el registro de todo lo que Booster crea en este Odoo.

Regla de oro del modelo Efficax: "lo nuestro se apaga; lo suyo jamas". Cada cosa que crees (agente, herramienta, usuario, automatizacion, registro) la registras con registrar_en_inventario y etiqueta 'creado_por_booster'. Lo que el cliente YA tenia antes de conocernos (camino C) se registra como 'preexistente' y esta PROHIBIDO tocarlo.

El kill-switch (killswitch_inventario) es la accion mas delicada de todo Booster:
- 'listar' es seguro: muestra que hay, siempre puedes usarlo para explicar al dueno que agrego Booster y que era suyo.
- 'apagar' archiva TODO lo creado por Booster y NADA de lo preexistente. Solo lo ejecutas con instruccion explicita de Efficax (fin de suscripcion) o del dueno, y SIEMPRE con confirmar=true despues de que la persona confirmo de forma explicita. Nunca lo hagas por iniciativa propia.
- 'reactivar' revierte el apagado (reconexion tras pago).
Despues de apagar o reactivar, reporta exactamente que se archivo/reactivo y que se salto (no archivable), en lenguaje de negocio.
"""


def _crear_modelo(o: Odoo) -> int:
    existente = o.execute("ir.model", "search", [("model", "=", "x_booster_inventario")])
    if existente:
        modelo_id = existente[0]
    else:
        modelo_id = o.execute("ir.model", "create", {"name": "Booster Inventario", "model": "x_booster_inventario", "state": "manual"})
        o.execute("ir.model.access", "create", {
            "name": "x_booster_inventario acceso base", "model_id": modelo_id,
            "perm_read": True, "perm_write": True, "perm_create": True, "perm_unlink": False,
        })
    existentes = {f["name"] for f in o.execute("ir.model.fields", "search_read", [("model_id", "=", modelo_id)], fields=["name"])}
    for campo in CAMPOS_INVENTARIO:
        if campo["name"] not in existentes:
            o.execute("ir.model.fields", "create", {**campo, "model_id": modelo_id, "state": "manual"})
            print("  campo creado:", campo["name"])
    return modelo_id


def _instalar_tool(o: Odoo, nombre: str, modelo_tecnico: str, codigo: str, descripcion: str, esquema: dict) -> int:
    model_id = o.execute("ir.model", "search", [("model", "=", modelo_tecnico)])[0]
    existentes = o.execute("ir.actions.server", "search", [("name", "=", nombre)])
    valores = {
        "name": nombre, "model_id": model_id, "state": "code", "code": codigo,
        "use_in_ai": True, "ai_tool_description": descripcion,
        "ai_tool_schema": json.dumps(esquema, ensure_ascii=False),
    }
    if existentes:
        o.execute("ir.actions.server", "write", existentes, valores)
        return existentes[0]
    return o.execute("ir.actions.server", "create", valores)


def instalar(o: Odoo) -> dict:
    from implementaciones.killswitch_inventario import CODIGO as CODIGO_KS  # noqa: PLC0415
    from implementaciones.registrar_en_inventario import CODIGO as CODIGO_REG  # noqa: PLC0415

    modelo_id = _crear_modelo(o)
    tool_reg = _instalar_tool(
        o, "booster: registrar_en_inventario", "x_booster_inventario", CODIGO_REG,
        "Registra en el inventario de Booster un registro recien creado (modelo + id + etiqueta creado_por_booster/preexistente + receta). "
        "Llamar SIEMPRE despues de crear cualquier cosa en el Odoo del cliente. Idempotente: registrar dos veces no duplica.",
        ESQUEMA_REGISTRAR,
    )
    tool_ks = _instalar_tool(
        o, "booster: killswitch_inventario", "x_booster_inventario", CODIGO_KS,
        "Kill-switch capa 2 de Booster sobre el inventario: 'listar' (seguro), 'apagar' (archiva TODO lo creado por Booster, NUNCA lo preexistente; requiere confirmar=true), "
        "'reactivar' (revierte). Es la accion mas delicada de Booster: apagar/reactivar solo con confirmacion explicita.",
        ESQUEMA_KILLSWITCH,
    )
    nombre_topic = "Booster — Inventario y kill-switch"
    existentes = o.execute("ai.topic", "search", [("name", "=", nombre_topic)])
    valores_topic = {"name": nombre_topic, "instructions": TOPIC_INSTRUCCIONES, "tool_ids": [(6, 0, [tool_reg, tool_ks])]}
    if existentes:
        o.execute("ai.topic", "write", existentes, valores_topic)
        topic_id = existentes[0]
    else:
        topic_id = o.execute("ai.topic", "create", valores_topic)
    agente = o.execute("ai.agent", "search", [("name", "=", "Booster")])
    o.execute("ai.agent", "write", agente, {"topic_ids": [(4, topic_id)]})  # (4,id): aditivo, nunca (6,0)
    topics = o.execute("ai.agent", "read", agente, fields=["topic_ids"])[0]["topic_ids"]
    return {"modelo_id": modelo_id, "tool_registrar": tool_reg, "tool_killswitch": tool_ks, "topic_id": topic_id, "topics_del_agente": topics}


if __name__ == "__main__":
    print("Inventario de Booster instalado:", instalar(Odoo()))
