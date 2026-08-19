"""Plan de contingencia de proveedor LLM — conmutacion manual instantanea.

Cuando OpenAI (u otro proveedor) se cae o responde con ReadTimeout, este
script cambia el motor de TODOS los agentes de Efficax de golpe, sin
tocar nada mas. La identidad del agente (nombre "Mentor", system_prompt
con el aviso de IA, temas, herramientas, historial de conversaciones)
vive en `ai.agent`, NO en el modelo -- asi que el cliente sigue hablando
con "Mentor" y no pierde familiaridad. Confirmado el 18-ago-2026: el
unico campo que cambia es `ai.agent.llm_model` (selection).

Uso:
    python conmutar_modelo.py estado              # ver que modelo tiene cada agente
    python conmutar_modelo.py gemini              # conmutar a Gemini 2.5 Pro (contingencia)
    python conmutar_modelo.py openai              # volver a GPT-5 (operacion normal)
    python conmutar_modelo.py gemini --solo Booster   # solo un agente

Criterio de eleccion (Alberto, 18-ago-2026): en contingencia usar "el
mas potente de Gemini de la lista de Odoo" -> gemini-2.5-pro. Los
modelos disponibles son los del selection de ai.agent.llm_model:
gpt-5 / gpt-5-mini / gpt-4.1 / gpt-4o / gemini-2.5-pro / gemini-2.5-flash.

Que NO hace: no cambia claves API (eso lo configura Odoo por tenant),
no toca prompts, ni temas, ni herramientas. Solo `llm_model`.
"""
from __future__ import annotations

import sys

from booster_rpc import Odoo

# Agentes de Efficax que participan en la contingencia. Los agentes de
# demo/de Odoo (Odoo Agent, Ask AI, etc.) se dejan como estan.
AGENTES_EFFICAX = ("Mentor Efficax (piloto)", "Booster")

PERFILES = {
    "openai": "gpt-5",           # operacion normal
    "gemini": "gemini-2.5-pro",  # contingencia: el mas potente de Google en Odoo
}


def _agentes(o: Odoo, solo: str | None):
    nombres = [solo] if solo else list(AGENTES_EFFICAX)
    return o.execute("ai.agent", "search_read", [("name", "in", nombres)], fields=["name", "llm_model"])


def estado(o: Odoo, solo: str | None = None) -> None:
    for a in _agentes(o, solo):
        print(f"  {a['name']:<28} -> {a['llm_model']}")


def conmutar(o: Odoo, perfil: str, solo: str | None = None) -> None:
    modelo = PERFILES[perfil]
    for a in _agentes(o, solo):
        if a["llm_model"] == modelo:
            print(f"  {a['name']:<28} ya estaba en {modelo}")
            continue
        o.execute("ai.agent", "write", [a["id"]], {"llm_model": modelo})
        print(f"  {a['name']:<28} {a['llm_model']} -> {modelo}")


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[1] not in ("estado", *PERFILES):
        print(__doc__)
        return 2
    solo = None
    if "--solo" in argv:
        solo = argv[argv.index("--solo") + 1]
    o = Odoo()
    if argv[1] == "estado":
        estado(o, solo)
    else:
        print(f"Conmutando a perfil '{argv[1]}' ({PERFILES[argv[1]]}):")
        conmutar(o, argv[1], solo)
        print("Verificacion:")
        estado(o, solo)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
