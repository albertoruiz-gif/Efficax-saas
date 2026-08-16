"""Utilidades RPC para instalar y probar herramientas de Booster contra un
Odoo real, reusando las mismas piezas que ya usa `generador.py`
(esquemas_odoo.sanear_para_odoo, guarda_llave.GUARDA_TEMPLATE).

No es parte del pipeline de producción — es la herramienta de quien
implementa, para el ciclo "instalar -> probar vigente -> probar
kill-switch -> verificar" descrito en `implementaciones/README.md`.

Credenciales: se leen de `scripts/credenciales_booster.env` (gitignored,
patrón `credenciales*`). Nunca hardcodear un valor acá.

Respeta el límite de la Política de Uso Aceptable de Odoo (~1 req/seg):
cada llamada de escritura hace una pausa corta antes de la siguiente.
"""
from __future__ import annotations

import importlib
import json
import pathlib
import sys
import time
import xmlrpc.client

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "server_actions"))

from esquemas_odoo import sanear_para_odoo  # noqa: E402

PAUSA_SEG = 1.1
CREDENCIALES_PATH = RAIZ / "scripts" / "credenciales_booster.env"

CATALOGO_PATH = (
    RAIZ.parent
    / "Efficax 2026 - 2027" / "EFFICAX_IA" / "Agentes_SAAS"
    / "agentes_v2" / "herramientas" / "herramientas_esquemas.json"
)


def cargar_credenciales() -> dict:
    valores = {}
    with open(CREDENCIALES_PATH, encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            k, v = linea.split("=", 1)
            valores[k] = v
    return valores


class Odoo:
    def __init__(self):
        c = cargar_credenciales()
        self.url = c["ODOO_URL"]
        self.db = c["ODOO_DB"]
        self.user = c["ODOO_USER"]
        self.key = c["ODOO_API_KEY"]
        common = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common")
        self.uid = common.authenticate(self.db, self.user, self.key, {})
        if not self.uid:
            raise RuntimeError("Autenticacion fallida contra Odoo")
        self.models = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object")

    def execute(self, modelo, metodo, *args, **kwargs):
        time.sleep(PAUSA_SEG)
        return self.models.execute_kw(self.db, self.uid, self.key, modelo, metodo, list(args), kwargs)


def cargar_catalogo() -> dict:
    return json.loads(CATALOGO_PATH.read_text(encoding="utf-8"))


def _limpiar_modelo(modelo: str) -> str:
    return modelo.split(" (")[0].strip()


def tool_del_catalogo(agente: str, nombre: str) -> dict:
    data = cargar_catalogo()
    for t in data["herramientas"][agente]:
        if t["name"] == nombre:
            return t, data.get("$defs", {})
    raise KeyError(f"{agente}/{nombre} no esta en el catalogo")


def construir_payload(agente: str, nombre: str, codigo_real: str) -> dict:
    """Igual que generador.construir_payload_ir_actions_server pero con el
    codigo REAL (guarda + logica) en vez del esqueleto TODO."""
    tool, defs = tool_del_catalogo(agente, nombre)
    schema_odoo = sanear_para_odoo(tool.get("input_schema", {}), defs)
    modelos = tool.get("modelos_odoo") or []
    modelo_tecnico = _limpiar_modelo(modelos[0]) if modelos else False
    return {
        "name": f"{agente}: {nombre}",
        "modelo_tecnico": modelo_tecnico,
        "code": codigo_real,
        "ai_tool_description": tool["description"],
        "ai_tool_schema": json.dumps(schema_odoo, ensure_ascii=False),
    }


def cargar_codigo_real(agente: str, nombre: str) -> str:
    mod = importlib.import_module(f"implementaciones.{agente}.{nombre}")
    return mod.CODIGO


def instalar_tool(o: Odoo, agente: str, nombre: str) -> int:
    """Crea o actualiza el ir.actions.server. Devuelve su id."""
    codigo = cargar_codigo_real(agente, nombre)
    payload = construir_payload(agente, nombre, codigo)
    model_ids = o.execute("ir.model", "search", [["model", "=", payload["modelo_tecnico"]]])
    if not model_ids:
        raise RuntimeError(f"Modelo tecnico no encontrado en Odoo: {payload['modelo_tecnico']}")
    existentes = o.execute("ir.actions.server", "search", [["name", "=", payload["name"]]])
    valores = {
        "name": payload["name"],
        "model_id": model_ids[0],
        "state": "code",
        "code": payload["code"],
        "use_in_ai": True,
        "ai_tool_description": payload["ai_tool_description"],
        "ai_tool_schema": payload["ai_tool_schema"],
    }
    if existentes:
        o.execute("ir.actions.server", "write", existentes, valores)
        return existentes[0]
    return o.execute("ir.actions.server", "create", valores)


def crear_o_actualizar_topic(o: Odoo, agent_id: int, name: str, instructions: str, tool_ids: list[int]) -> int:
    existentes = o.execute("ai.topic", "search", [["name", "=", name]])
    valores = {"name": name, "instructions": instructions, "tool_ids": [(6, 0, tool_ids)]}
    if existentes:
        o.execute("ai.topic", "write", existentes, valores)
        topic_id = existentes[0]
    else:
        topic_id = o.execute("ai.topic", "create", valores)
    agente_topics = o.execute("ai.agent", "read", [agent_id], fields=["topic_ids"])[0]["topic_ids"]
    if topic_id not in agente_topics:
        o.execute("ai.agent", "write", [agent_id], {"topic_ids": [(4, topic_id)]})
    return topic_id


def licencia_id(o: Odoo) -> int:
    ids = o.execute("x_booster_licencia", "search", [], limit=1)
    if not ids:
        raise RuntimeError("No hay registro en x_booster_licencia")
    return ids[0]


def set_licencia_vigente(o: Odoo):
    lic = licencia_id(o)
    import datetime as _dt
    o.execute("x_booster_licencia", "write", [lic], {
        "x_fecha_renovacion": _dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    })


def set_licencia_vencida(o: Odoo, horas: int = 72):
    lic = licencia_id(o)
    import datetime as _dt
    vencida = _dt.datetime.utcnow() - _dt.timedelta(hours=horas)
    o.execute("x_booster_licencia", "write", [lic], {
        "x_fecha_renovacion": vencida.strftime("%Y-%m-%d %H:%M:%S")
    })


def leer_licencia(o: Odoo) -> dict:
    lic = licencia_id(o)
    return o.execute("x_booster_licencia", "read", [lic], fields=["x_fecha_renovacion", "x_tenant"])[0]
