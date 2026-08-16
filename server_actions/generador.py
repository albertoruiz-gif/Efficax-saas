"""Generador de payloads de Server Actions desde el catálogo JSON.

Lee `herramientas_esquemas.json` (58 herramientas, spec fuente de verdad) y
genera, por herramienta:

- si `ejecuta == "server_action"`: un JSON con el payload real y completo
  para crear/actualizar un `ir.actions.server` en Odoo 19 como herramienta
  de IA — mapeo validado en vivo en Efficax el 15-ago-2026 (ver receta 7 en
  `01-booster-implementador.md` y el README de `herramientas/`):
    name, modelo_tecnico (Booster lo resuelve a model_id via ir.model.search
    en el momento de instalar — este generador no requiere conexión a Odoo),
    state="code", code (con la guarda de llave embebida — NUNCA sudo salvo
    la guarda misma), use_in_ai=True, ai_tool_description, ai_tool_schema.
- si `ejecuta == "servidor_control"`: un esqueleto .py (no es un Server
  Action de Odoo — es un endpoint del microservicio en servidor_control/).

Uso:
    python generador.py --catalogo <ruta a herramientas_esquemas.json> --salida ./generadas
    (si se omite --catalogo, usa CATALOGO_DEFAULT — ver abajo)
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib

from esquemas_odoo import sanear_para_odoo
from guarda_llave import GUARDA_TEMPLATE

# La spec vive fuera de este repo (en EFFICAX_IA, junto al resto de la
# documentación de agentes en markdown). Es una dependencia cross-repo
# frágil por diseño de carpetas, no por accidente — queda documentada acá
# y en server_actions/README.md en vez de asumirse en silencio. Override
# posible con la variable de entorno EFFICAX_CATALOGO.
CATALOGO_DEFAULT = (
    pathlib.Path(__file__).resolve().parents[2]
    / "Efficax 2026 - 2027" / "EFFICAX_IA" / "Agentes_SAAS"
    / "agentes_v2" / "herramientas" / "herramientas_esquemas.json"
)


def catalogo_path() -> pathlib.Path:
    """Resuelve la ruta del catálogo: EFFICAX_CATALOGO si está seteada, si no
    CATALOGO_DEFAULT. Centralizado acá para que CLI y tests usen la misma
    lógica de resolución (evita que los tests validen un default que el
    entrypoint real no usa, o viceversa)."""
    override = os.environ.get("EFFICAX_CATALOGO")
    return pathlib.Path(override) if override else CATALOGO_DEFAULT

CODE_TEMPLATE = '''{guarda}
# TODO implementar la logica real de "{tool_name}" (agente: {agente})
# Parametros disponibles como variables sueltas (Odoo los inyecta desde
# ai_tool_schema, no hace falta desempaquetar nada): {params}
# No elevar privilegios aca abajo (nada de sudo) — el usuario real es quien le habla al agente.
# Al terminar, entregar el resultado con la forma de respuesta_estandar:
ai['result'] = {{'ok': False, 'mensaje': 'no implementado todavia', 'datos': {{}}}}
'''

ESQUELETO_SERVIDOR_CONTROL = '''"""Endpoint del Servidor de Control: {name} (agente: {agente})

{description}

Aprobación: {aprobacion}
Entrada (JSON Schema): ver catálogo — required: {required}
Salida: respuesta_estandar {{ok, mensaje, datos}}

GENERADO desde herramientas_esquemas.json — la spec manda; si esto diverge
del catálogo, se regenera, no se parcha a mano.
"""
# TODO: implementar como ruta FastAPI en servidor_control/app/
'''


def _limpiar_modelo(modelo: str) -> str:
    """'helpdesk.ticket (Casa Efficax)' -> 'helpdesk.ticket'."""
    return modelo.split(" (")[0].strip()


def construir_payload_ir_actions_server(tool: dict, agente: str, defs: dict) -> dict:
    # El esquema que ve Odoo NO es el del catálogo: Odoo sólo acepta un
    # subconjunto de JSON Schema (ver esquemas_odoo.py). Los nombres de los
    # parámetros que recibe el código son los del esquema SANEADO, porque son
    # los que Odoo inyecta como variables.
    schema_odoo = sanear_para_odoo(tool.get("input_schema", {}), defs)
    props = list(schema_odoo["properties"].keys())
    modelos = tool.get("modelos_odoo") or []
    modelo_tecnico = _limpiar_modelo(modelos[0]) if modelos else False
    codigo = CODE_TEMPLATE.format(
        guarda=GUARDA_TEMPLATE,
        tool_name=tool["name"],
        agente=agente,
        params=", ".join(props) if props else "(sin parametros)",
    )
    return {
        "name": f"{agente}: {tool['name']}",
        "modelo_tecnico": modelo_tecnico,
        "state": "code",
        "code": codigo,
        "use_in_ai": True,
        "ai_tool_description": tool["description"],
        "ai_tool_schema": json.dumps(schema_odoo, ensure_ascii=False),
        "_meta": {
            "agente": agente,
            "aprobacion": tool["aprobacion"],
            "ejecuta": tool["ejecuta"],
        },
    }


def generar(catalogo: pathlib.Path, salida: pathlib.Path) -> dict:
    data = json.loads(catalogo.read_text(encoding="utf-8"))
    defs = data.get("$defs", {})
    salida.mkdir(parents=True, exist_ok=True)
    n_server_action = 0
    n_servidor_control = 0
    for agente, tools in data["herramientas"].items():
        carpeta = salida / agente
        carpeta.mkdir(exist_ok=True)
        for t in tools:
            if t["ejecuta"] == "server_action":
                payload = construir_payload_ir_actions_server(t, agente, defs)
                (carpeta / f"{t['name']}.json").write_text(
                    json.dumps(payload, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                n_server_action += 1
            else:  # servidor_control
                sub = carpeta / "_servidor_control"
                sub.mkdir(exist_ok=True)
                body = ESQUELETO_SERVIDOR_CONTROL.format(
                    name=t["name"],
                    agente=agente,
                    description=t["description"],
                    aprobacion=t["aprobacion"],
                    required=t["input_schema"].get("required", []),
                )
                (sub / f"{t['name']}.py").write_text(body, encoding="utf-8")
                n_servidor_control += 1
    return {
        "ir_actions_server": n_server_action,
        "servidor_control": n_servidor_control,
        "total": n_server_action + n_servidor_control,
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--catalogo", type=pathlib.Path, default=catalogo_path())
    p.add_argument("--salida", default=pathlib.Path("generadas"), type=pathlib.Path)
    args = p.parse_args()
    resumen = generar(args.catalogo, args.salida)
    print(
        f"{resumen['total']} herramientas generadas en {args.salida} "
        f"({resumen['ir_actions_server']} payloads ir.actions.server, "
        f"{resumen['servidor_control']} esqueletos de Servidor de Control)"
    )
