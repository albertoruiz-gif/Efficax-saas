"""Generador de esqueletos de Server Actions desde el catálogo JSON.

Lee `herramientas_esquemas.json` (las 49 herramientas, spec fuente de verdad)
y genera un archivo .py por herramienta con: docstring de contrato, guarda de
llave, validación de entrada según su input_schema y el respuesta_estandar.

Uso:
    python generador.py --catalogo ../../Agentes_SAAS/agentes_v2/herramientas/herramientas_esquemas.json --salida ./generadas
"""
from __future__ import annotations

import argparse
import json
import pathlib

from guarda_llave import GUARDA_TEMPLATE

PLANTILLA = '''"""Server Action: {name} (agente: {agente})

{description}

Ejecuta en: {ejecuta} · Aprobación: {aprobacion}
Modelos Odoo: {modelos}
Entrada (JSON Schema): ver catálogo — required: {required}
Salida: respuesta_estandar {{ok, mensaje, datos}}

GENERADO desde herramientas_esquemas.json — la spec manda; si esto diverge
del catálogo, se regenera, no se parcha a mano.
"""
# --- código de la Server Action (Odoo: variables env, model, records) ---

{guarda}
# TODO implementar según la spec del agente ({agente})
'''


def generar(catalogo: pathlib.Path, salida: pathlib.Path) -> int:
    data = json.loads(catalogo.read_text(encoding="utf-8"))
    salida.mkdir(parents=True, exist_ok=True)
    n = 0
    for agente, tools in data["herramientas"].items():
        carpeta = salida / agente
        carpeta.mkdir(exist_ok=True)
        for t in tools:
            body = PLANTILLA.format(
                name=t["name"],
                agente=agente,
                description=t["description"],
                ejecuta=t["ejecuta"],
                aprobacion=t["aprobacion"],
                modelos=", ".join(t.get("modelos_odoo", [])),
                required=t["input_schema"].get("required", []),
                guarda=GUARDA_TEMPLATE,
            )
            (carpeta / f"{t['name']}.py").write_text(body, encoding="utf-8")
            n += 1
    return n


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--catalogo", required=True, type=pathlib.Path)
    p.add_argument("--salida", default=pathlib.Path("generadas"), type=pathlib.Path)
    args = p.parse_args()
    total = generar(args.catalogo, args.salida)
    print(f"{total} esqueletos generados en {args.salida}")
