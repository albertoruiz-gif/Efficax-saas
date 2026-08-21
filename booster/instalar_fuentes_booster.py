"""Instala las FUENTES reales del agente Booster (`ai.agent.source`).

El agente Booster se creo (`instalar_booster_fase1.py`) con
`restrict_to_sources=True` pero sin ninguna fuente -- verificado en vivo
el 19-ago-2026 (`sources_ids: []`). El spec (`01-booster-implementador.md`)
dice que debe alimentarse de "guias de implementacion Efficax,
instructivos Pack 360, plantillas RF-10". Busque esos tres documentos en
el repo cross-repo de Efficax y **Pack 360 y las plantillas RF-10 no
existen como archivos** -- el spec los menciona pero nunca se escribieron.
No se inventa su contenido (misma convencion que el resto del catalogo).

**Ruta canonica (21-ago-2026, pedido de Alberto):** `booster/fuentes/` es
LA carpeta donde deben vivir los documentos que Booster consume como
fuente -- no sueltos en la raiz de `booster/` mezclados con scripts y
README. Este instalador escanea esa carpeta con glob (`*.md`), no una
lista fija en codigo: para agregar una fuente nueva (ej. cuando lleguen
Pack 360 o las plantillas RF-10), basta con soltar el archivo ahi y
volver a correr `python instalar_fuentes_booster.py` -- no hace falta
tocar este script.

Primera version honesta, con los DOS documentos reales y verificados que
ya existian en este repo y son relevantes para lo que Booster conversa
hoy (Fase 1 + Fase 1-bis), movidos a `booster/fuentes/`:

1. `NORMA-IMPLEMENTACION.md` -- la norma de 6 fases que
   `evaluar_implementacion` usa; Booster necesita conocerla para explicar
   sus hallazgos con criterio, no solo repetir el JSON de la herramienta.
2. `UX-ONBOARDING.md` -- el detalle de los 3 caminos A/B/C, el porque el
   checkout va antes de tocar nada tecnico, y el Protocolo Produccion
   (RF-20) para clientes que ya operan.

Pendiente (no instalado aca, requiere que Alberto los provea o confirme):
Pack 360 y plantillas RF-10 -- ver README.md, seccion "Fuentes del
agente Booster".

Cada fuente se sube como `ai.agent.source` tipo 'binary' con un
`ir.attachment` real (no una URL ni texto pegado) -- mismo mecanismo que
usa Odoo para cualquier documento indexado por IA.

Uso:
    python instalar_fuentes_booster.py
"""
from __future__ import annotations

import base64
import pathlib
import sys
import time

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
from booster_rpc import Odoo  # noqa: E402

FUENTES_DIR = RAIZ / "booster" / "fuentes"


def documentos() -> list[pathlib.Path]:
    """Cualquier .md dentro de booster/fuentes/ es una fuente a instalar --
    sin lista fija, para que agregar un documento nuevo no requiera tocar
    codigo (ver docstring del modulo)."""
    if not FUENTES_DIR.is_dir():
        raise RuntimeError(f"No existe {FUENTES_DIR} -- crear la carpeta y poner ahi los documentos fuente.")
    return sorted(FUENTES_DIR.glob("*.md"))


def instalar_fuente(o: Odoo, agente_id: int, ruta: pathlib.Path) -> dict:
    contenido = ruta.read_text(encoding="utf-8")
    b64 = base64.b64encode(contenido.encode("utf-8")).decode("ascii")

    # Idempotente: si ya existe una fuente con este nombre de archivo para
    # este agente, se reemplaza el adjunto (nuevo contenido) en vez de
    # duplicar la fuente.
    existentes = o.execute(
        "ai.agent.source", "search",
        [("agent_id", "=", agente_id), ("name", "=", ruta.name)],
    )

    if existentes:
        fuente = o.execute("ai.agent.source", "read", existentes, fields=["attachment_id"])[0]
        o.execute("ir.attachment", "write", [fuente["attachment_id"][0]], {
            "datas": b64,
            "mimetype": "text/markdown",
        })
        source_id = existentes[0]
    else:
        attachment_id = o.execute("ir.attachment", "create", {
            "name": ruta.name,
            "datas": b64,
            "mimetype": "text/markdown",
        })
        source_id = o.execute("ai.agent.source", "create", {
            "agent_id": agente_id,
            "type": "binary",
            "attachment_id": attachment_id,
            "name": ruta.name,
        })

    return {"source_id": source_id, "archivo": ruta.name}


def esperar_indexado(o: Odoo, source_id: int, intentos: int = 10, espera_seg: int = 3) -> str:
    for _ in range(intentos):
        estado = o.execute("ai.agent.source", "read", [source_id], fields=["status", "error_details"])[0]
        if estado["status"] in ("indexed", "failed"):
            return estado["status"] + (f" -- {estado['error_details']}" if estado.get("error_details") else "")
        time.sleep(espera_seg)
    return "processing (no termino de indexar en el tiempo de espera)"


def instalar(o: Odoo) -> list[dict]:
    agente = o.execute("ai.agent", "search", [("name", "=", "Booster")])
    if not agente:
        raise RuntimeError("El agente Booster no existe -- correr antes instalar_booster_fase1.py")
    agente_id = agente[0]

    docs = documentos()
    if not docs:
        print(f"AVISO: {FUENTES_DIR} esta vacia -- nada que instalar.")
        return []

    resultados = []
    for ruta in docs:
        r = instalar_fuente(o, agente_id, ruta)
        resultados.append(r)
        print(f"Fuente instalada: {r['archivo']} (source_id {r['source_id']}) -- esperando indexado...")
        estado = esperar_indexado(o, r["source_id"])
        r["estado_indexado"] = estado
        print(f"  -> {estado}")

    return resultados


if __name__ == "__main__":
    o = Odoo()
    resultado = instalar(o)
    print("\nFuentes de Booster instaladas:", resultado)
